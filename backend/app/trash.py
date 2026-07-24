"""Papelera de Martix: ningun borrado es definitivo.

Martix administra documentos personales (declaraciones, contratos, fotos), asi
que ninguna de sus rutas de borrado -- mantenimiento por antiguedad, limpieza
de duplicados y borrado desde el analizador de espacio -- puede usar unlink()
o rmtree() directamente. Un fallo de configuracion (una regla de mantenimiento
apuntando a la carpeta equivocada) seria irreversible.

Estrategia:

1. Si el sistema tiene `send2trash`, se usa la papelera NATIVA del escritorio:
   el usuario recupera los archivos desde su gestor de archivos habitual.
2. Si no, se mueven a una cuarentena propia bajo la carpeta de datos de
   Martix, con un indice JSON que permite restaurarlos desde la interfaz.

En ambos casos se registra el borrado para poder deshacerlo.
"""

import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from config.settings import TRASH_DIR, TRASH_RETENTION_DAYS

logger = logging.getLogger("martix.trash")

try:  # opcional: papelera nativa del escritorio
    from send2trash import send2trash as _send2trash_native
except Exception:  # pragma: no cover - depende del entorno
    _send2trash_native = None

_INDEX_NAME = "index.json"
_lock = threading.Lock()


def native_trash_available() -> bool:
    return _send2trash_native is not None


def _index_path() -> Path:
    return TRASH_DIR / _INDEX_NAME


def _read_index() -> list[dict]:
    path = _index_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        logger.warning("indice de papelera ilegible; se empieza uno nuevo")
        return []


def _write_index(entries: list[dict]) -> None:
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _index_path().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_index_path())


def _unique_slot(name: str) -> Path:
    """Carpeta unica dentro de la cuarentena para un elemento borrado."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    counter = 0
    while True:
        suffix = f"-{counter}" if counter else ""
        slot = TRASH_DIR / f"{stamp}{suffix}-{os.getpid()}"
        if not slot.exists():
            slot.mkdir(parents=True)
            return slot
        counter += 1


def move_to_trash(path: Path) -> dict:
    """Envia un archivo o carpeta a la papelera.

    Devuelve {"method": "native"|"quarantine", "entry_id": str|None}.
    Lanza OSError si no se pudo mover.
    """
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        raise FileNotFoundError(f"no existe: {path}")

    if _send2trash_native is not None:
        try:
            _send2trash_native(str(path))
            logger.info("enviado a la papelera del sistema: %s", path)
            return {"method": "native", "entry_id": None}
        except Exception as exc:
            logger.warning("papelera nativa fallo para %s (%s); se usa cuarentena", path, exc)

    with _lock:
        slot = _unique_slot(path.name)
        destination = slot / path.name
        shutil.move(str(path), str(destination))

        entry = {
            "id": slot.name,
            "name": path.name,
            "original_path": str(path),
            "trashed_path": str(destination),
            "is_dir": destination.is_dir(),
            "deleted_at": datetime.now().isoformat(timespec="seconds"),
        }
        entries = _read_index()
        entries.append(entry)
        _write_index(entries)

    logger.info("movido a la cuarentena de Martix: %s -> %s", path, destination)
    return {"method": "quarantine", "entry_id": entry["id"]}


def list_trash() -> list[dict]:
    """Elementos recuperables de la cuarentena propia, del mas reciente al mas antiguo."""
    entries = []
    for entry in _read_index():
        trashed = Path(entry.get("trashed_path", ""))
        if trashed.exists():
            try:
                size = _tree_size(trashed)
            except OSError:
                size = 0
            entries.append({**entry, "size_bytes": size})
    entries.sort(key=lambda e: e.get("deleted_at", ""), reverse=True)
    return entries


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except OSError:
                continue
    return total


def restore(entry_id: str) -> tuple[dict | None, str | None]:
    """Devuelve un elemento de la cuarentena a su ruta original.
    Retorna (entrada, error)."""
    with _lock:
        entries = _read_index()
        match = next((e for e in entries if e.get("id") == entry_id), None)
        if match is None:
            return None, "elemento no encontrado en la papelera"

        trashed = Path(match["trashed_path"])
        if not trashed.exists():
            return None, "el elemento ya no esta en la papelera"

        original = Path(match["original_path"])
        try:
            original.parent.mkdir(parents=True, exist_ok=True)
            final = original
            counter = 1
            while final.exists():
                final = original.parent / f"{original.stem} (restaurado {counter}){original.suffix}"
                counter += 1
            shutil.move(str(trashed), str(final))
        except OSError as exc:
            return None, f"no se pudo restaurar: {exc}"

        shutil.rmtree(trashed.parent, ignore_errors=True)
        _write_index([e for e in entries if e.get("id") != entry_id])
        return {**match, "restored_to": str(final)}, None


def purge(entry_id: str | None = None, older_than_days: int | None = None) -> int:
    """Borra definitivamente. Sin argumentos purga solo lo caducado.
    Devuelve cuantas entradas se eliminaron."""
    if older_than_days is None:
        older_than_days = TRASH_RETENTION_DAYS

    with _lock:
        entries = _read_index()
        kept, removed = [], 0
        cutoff = time.time() - older_than_days * 86400

        for entry in entries:
            trashed = Path(entry.get("trashed_path", ""))
            should_remove = False
            if entry_id is not None:
                should_remove = entry.get("id") == entry_id
            else:
                try:
                    deleted_at = datetime.fromisoformat(entry.get("deleted_at", "")).timestamp()
                except ValueError:
                    deleted_at = 0.0
                should_remove = deleted_at < cutoff

            if should_remove:
                shutil.rmtree(trashed.parent, ignore_errors=True)
                removed += 1
            elif trashed.exists():
                kept.append(entry)

        _write_index(kept)
    return removed
