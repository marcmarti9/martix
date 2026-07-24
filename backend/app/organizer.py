"""Decide el destino final de un archivo (reglas del usuario primero, si no
el clasificador inteligente), lo mueve de forma segura sin pisar archivos
con el mismo nombre, y permite deshacer un movimiento del historial."""

import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import tarfile
import threading
import time
import zipfile
from pathlib import Path

from app import db
from app.browser import resolve_safe_path
from app.classifier import classify, normalize, _extract_content, extract_metadata
from app.security import safe_destination_dir
from config.settings import DOWNLOADS_DIR, HOME_DIR, IGNORED_SUFFIXES, is_temporary_download_file, is_file_in_use

logger = logging.getLogger("martix.organizer")


def calculate_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
    except OSError:
        pass
    return h.hexdigest()


def calculate_fast_hash(path: Path) -> str:
    h = hashlib.sha256()
    CHUNK = 64 * 1024
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            if size <= CHUNK * 2:
                h.update(f.read())
            else:
                h.update(f.read(CHUNK))
                f.seek(size - CHUNK)
                h.update(f.read(CHUNK))
        return h.hexdigest()
    except OSError:
        return ""


def get_default_scan_dirs() -> list[Path]:
    dirs = set()
    dirs.add(DOWNLOADS_DIR.resolve())
    try:
        from config.settings import load_categories
        categories = load_categories()["categories"]
        for cat in categories.values():
            folder_str = cat.get("folder")
            if folder_str:
                from app.security import safe_destination_dir
                resolved = safe_destination_dir(folder_str)
                if resolved and resolved.exists():
                    dirs.add(resolved.resolve())
    except Exception:
        pass
    try:
        for topic in db.list_topics():
            folder_str = topic.get("destination")
            if folder_str:
                from app.security import safe_destination_dir
                resolved = safe_destination_dir(folder_str)
                if resolved and resolved.exists():
                    dirs.add(resolved.resolve())
    except Exception:
        pass
    return list(dirs)


def find_duplicates(directories: list[Path] | None = None) -> list[dict]:
    """Busca archivos duplicados agrupando por tamaño, luego fast-hash, y finalmente hash completo."""
    if directories is None:
        directories = get_default_scan_dirs()

    files = []
    seen_paths = set()
    for root_dir in directories:
        if not root_dir.exists() or not root_dir.is_dir():
            continue
        for root, dirs, filenames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in filenames:
                if f.startswith('.'):
                    continue
                if Path(f).suffix.lower() in IGNORED_SUFFIXES:
                    continue
                file_path = Path(root) / f
                try:
                    resolved = file_path.resolve()
                    if resolved not in seen_paths and resolved.is_file():
                        seen_paths.add(resolved)
                        files.append(resolved)
                except OSError:
                    continue

    by_size = {}
    for path in files:
        try:
            size = path.stat().st_size
            if size == 0:
                continue
            by_size.setdefault(size, []).append(path)
        except OSError:
            continue

    candidate_size_groups = [paths for size, paths in by_size.items() if len(paths) > 1]

    by_fast_hash = {}
    for paths in candidate_size_groups:
        fast_groups = {}
        for path in paths:
            fh = calculate_fast_hash(path)
            if fh:
                fast_groups.setdefault(fh, []).append(path)
        for fh, fh_paths in fast_groups.items():
            if len(fh_paths) > 1:
                by_fast_hash[fh] = fh_paths

    duplicate_groups = {}
    for fh, paths in by_fast_hash.items():
        full_hash_groups = {}
        for path in paths:
            sha = calculate_sha256(path)
            if sha:
                full_hash_groups.setdefault(sha, []).append(path)
        for sha, sha_paths in full_hash_groups.items():
            if len(sha_paths) > 1:
                size = sha_paths[0].stat().st_size
                file_entries = []
                for p in sha_paths:
                    try:
                        rel_path = str(p.relative_to(HOME_DIR.resolve())).replace("\\", "/")
                    except ValueError:
                        rel_path = str(p).replace("\\", "/")
                    try:
                        mtime_str = datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")
                    except OSError:
                        mtime_str = ""
                    file_entries.append({
                        "path": rel_path,
                        "name": p.name,
                        "mtime": mtime_str
                    })
                file_entries.sort(key=lambda x: x["path"])
                duplicate_groups[sha] = {
                    "hash": sha,
                    "size_bytes": size,
                    "files": file_entries
                }

    result = list(duplicate_groups.values())
    result.sort(key=lambda g: g["size_bytes"], reverse=True)
    return result



def unpack_archive(archive_path: Path, extract_dir: Path) -> None:
    """Desempaqueta un archivo comprimido de forma segura validando contra Zip-Slip / Path Traversal."""
    extract_dir_abs = os.path.abspath(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    name_lower = archive_path.name.lower()

    if zipfile.is_zipfile(archive_path) or name_lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            for member in zf.infolist():
                member_path = os.path.abspath(os.path.join(extract_dir_abs, member.filename))
                if not (member_path == extract_dir_abs or member_path.startswith(extract_dir_abs + os.sep)):
                    raise ValueError(f"Zip-Slip detectado en archivo zip: {member.filename}")
            zf.extractall(extract_dir_abs)
    elif tarfile.is_tarfile(archive_path) or name_lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".gz")):
        with tarfile.open(archive_path, "r:*") as tf:
            for member in tf.getmembers():
                member_path = os.path.abspath(os.path.join(extract_dir_abs, member.name))
                if not (member_path == extract_dir_abs or member_path.startswith(extract_dir_abs + os.sep)):
                    raise ValueError(f"Zip-Slip detectado en archivo tar: {member.name}")
                # Los symlinks/hardlinks pueden apuntar fuera del directorio de
                # extraccion aunque su propio nombre sea seguro; se valida el
                # destino del enlace por separado (CVE-2007-4559 style).
                if member.issym():
                    link_target = os.path.abspath(os.path.join(os.path.dirname(member_path), member.linkname))
                elif member.islnk():
                    link_target = os.path.abspath(os.path.join(extract_dir_abs, member.linkname))
                else:
                    link_target = None
                if link_target is not None and not (
                    link_target == extract_dir_abs or link_target.startswith(extract_dir_abs + os.sep)
                ):
                    raise ValueError(f"Enlace inseguro detectado en archivo tar: {member.name} -> {member.linkname}")
            tf.extractall(extract_dir_abs)
    else:
        raise ValueError(f"Formato de archivo comprimido no soportado: {archive_path}")


def check_conditions(path: Path, ext: str, conditions_str: str | None) -> bool:
    if not conditions_str:
        return True # Si no hay condiciones adicionales, es un match directo
    try:
        conditions = json.loads(conditions_str)
    except Exception:
        return False
    if not isinstance(conditions, list):
        return False

    for cond in conditions:
        field = cond.get("field")
        op = cond.get("operator")
        val = cond.get("value")
        if not field or not op:
            continue

        actual = None
        if field == "name":
            actual = path.name
        elif field == "stem":
            actual = path.stem
        elif field == "extension":
            actual = ext
        elif field == "size_kb":
            try:
                actual = path.stat().st_size / 1024
            except OSError:
                return False
        elif field == "age_days":
            try:
                actual = (time.time() - path.stat().st_mtime) / 86400
            except OSError:
                return False
        elif field == "content":
            actual = _extract_content(path, ext)
        elif field in ("artist", "album", "title", "year", "camera", "exif_date"):
            meta = extract_metadata(path)
            actual = meta.get(field)

        if actual is None:
            return False

        if op == "contains":
            if not isinstance(actual, str) or normalize(val) not in normalize(actual):
                return False
        elif op == "not_contains":
            if not isinstance(actual, str) or normalize(val) in normalize(actual):
                return False
        elif op in ("equals", "=="):
            try:
                if float(actual) != float(val):
                    return False
            except (ValueError, TypeError):
                if normalize(str(actual)) != normalize(str(val)):
                    return False
        elif op == "starts_with":
            if not isinstance(actual, str) or not normalize(actual).startswith(normalize(val)):
                return False
        elif op == "ends_with":
            if not isinstance(actual, str) or not normalize(actual).endswith(normalize(val)):
                return False
        elif op in ("gt", ">"):
            try:
                if float(actual) <= float(val):
                    return False
            except (ValueError, TypeError):
                return False
        elif op in ("lt", "<"):
            try:
                if float(actual) >= float(val):
                    return False
            except (ValueError, TypeError):
                return False
        elif op in ("gte", ">="):
            try:
                if float(actual) < float(val):
                    return False
            except (ValueError, TypeError):
                return False
        elif op in ("lte", "<="):
            try:
                if float(actual) > float(val):
                    return False
            except (ValueError, TypeError):
                return False
    return True


def format_rename_pattern(pattern: str, path: Path, category: str, topic_name: str | None) -> str:
    now = datetime.datetime.now()
    try:
        mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        mtime = now

    meta = extract_metadata(path)

    placeholders = {
        "{YYYY}": now.strftime("%Y"),
        "{MM}": now.strftime("%m"),
        "{DD}": now.strftime("%d"),
        "{FILE_YYYY}": mtime.strftime("%Y"),
        "{FILE_MM}": mtime.strftime("%m"),
        "{FILE_DD}": mtime.strftime("%d"),
        "{OriginalName}": path.stem,
        "{Topic}": topic_name or "",
        "{Category}": category,
        "{ext}": path.suffix.lower().lstrip("."),
        "{ARTIST}": meta.get("artist") or "",
        "{ALBUM}": meta.get("album") or "",
        "{TITLE}": meta.get("title") or "",
        "{CAMERA}": meta.get("camera") or "",
        "{EXIF_DATE}": meta.get("exif_date") or "",
        "{YEAR}": meta.get("year") or "",
        "{year}": meta.get("year") or "",
    }

    new_name = pattern
    for placeholder, val in placeholders.items():
        new_name = new_name.replace(placeholder, val)

    # Si el patron no especifica la extension y el archivo original tiene una, se la anadimos
    if not Path(new_name).suffix and path.suffix:
        new_name += path.suffix

    # Sanitizar el nombre del archivo final
    new_name = re.sub(r'[\x00/\\:*?"<>|]', '_', new_name)
    return new_name


def resolve_destination_folder(path: Path) -> tuple[str, str, str | None]:
    """Devuelve (categoria, carpeta_relativa_a_home, rename_pattern) para un archivo dado."""
    ext = path.suffix.lower().lstrip(".")

    # Buscar en todas las reglas personalizadas (incluyendo condicionales)
    rules = db.list_rules()
    for rule in rules:
        rule_ext = rule.get("extension")
        # Si la regla especifica una extension concreta (y no es wildcard *), debe coincidir
        if rule_ext and rule_ext != "*" and rule_ext != ext:
            continue
        # Comprobar condiciones (AND)
        if check_conditions(path, ext, rule.get("conditions")):
            return "regla personalizada", rule["destination"], rule.get("rename_pattern")

    # Clasificar con el categorizador inteligente
    result = classify(path)
    return result["category"], result["folder"], result.get("rename_pattern")


# El watcher lanza varios workers concurrentes (y el scheduler/API pueden
# organizar en paralelo a ellos), asi que elegir un nombre de destino libre
# y mover el archivo debe ser una seccion critica: sin este lock, dos hilos
# podrian ver el mismo destino como libre a la vez (check-then-act) y uno
# pisaria silenciosamente el archivo del otro con shutil.move.
_move_lock = threading.Lock()


def _unique_destination(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem, suffix = Path(filename).stem, Path(filename).suffix
    counter = 1
    while dest.exists():
        dest = dest_dir / f"{stem} ({counter}){suffix}"
        counter += 1
    return dest


def is_destination_or_reserved_dir(path: Path) -> bool:
    """Comprueba si un directorio es una carpeta de sistema, reservada o una
    carpeta de destino activa para evitar mover carpetas del sistema o provocar bucles."""
    if not path.is_dir():
        return False
    if path.name.startswith("."):
        return True
    if is_temporary_download_file(path):
        return True
    if path.name in ("node_modules", ".venv", "__pycache__", ".git", "scratch", "dist", "build"):
        return True

    try:
        resolved = path.resolve()
        if resolved in (HOME_DIR.resolve(), DOWNLOADS_DIR.resolve()):
            return True

        scan_dirs = get_default_scan_dirs()
        for d in scan_dirs:
            if resolved == d.resolve():
                return True
    except (OSError, ValueError):
        pass

    return False


def organize_folder(path: Path) -> dict | None:
    """Mueve una carpeta completa a su destino según reglas o clasificación."""
    if not path.exists() or not path.is_dir():
        return None

    if is_destination_or_reserved_dir(path):
        return None

    if is_file_in_use(path):
        return None

    category, relative_folder, rename_pattern = resolve_destination_folder(path)
    dest_dir = safe_destination_dir(relative_folder)
    if dest_dir is None:
        logger.warning("destino invalido %r para carpeta %s; no se mueve", relative_folder, path.name)
        return None

    if dest_dir.resolve() == path.parent.resolve() or dest_dir.resolve() == path.resolve():
        return None

    topic_name = category.split(": ", 1)[1] if category.startswith("tema: ") else None
    if rename_pattern:
        dest_filename = format_rename_pattern(rename_pattern, path, category, topic_name)
    else:
        dest_filename = path.name

    with _move_lock:
        destination = _unique_destination(dest_dir, dest_filename)
        if destination.resolve() == path.resolve():
            return None

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            source_str = str(path)
            shutil.move(source_str, str(destination))
        except OSError as exc:
            logger.error("no se pudo mover carpeta %s: %s", path.name, exc)
            return None

    db.log_move(
        filename=path.name,
        source=source_str,
        destination=str(destination),
        category=category,
    )
    return {
        "filename": path.name,
        "source": source_str,
        "destination": str(destination),
        "category": category,
        "is_dir": True,
    }


def organize_file(path: Path) -> dict | None:
    """Mueve un archivo o carpeta a su ubicación correspondiente. Devuelve info del
    movimiento, o None si no se movio (ya no existe, destino invalido,
    o ya esta en su carpeta de destino)."""
    if not path.exists():
        return None

    if path.is_dir():
        return organize_folder(path)

    if not path.is_file():
        return None

    if is_temporary_download_file(path):
        return None

    try:
        if path.stat().st_size == 0:
            return None
    except OSError:
        return None

    if is_file_in_use(path):
        return None

    name_lower = path.name.lower()
    is_archive = name_lower.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".gz"))
    unpack_enabled = str(db.get_setting("unpack_archives", "true")).lower() in ("true", "1")

    if is_archive and unpack_enabled:
        if name_lower.endswith(".tar.gz"):
            folder_name = path.name[:-7]
        elif name_lower.endswith(".tgz"):
            folder_name = path.name[:-4]
        else:
            folder_name = path.stem

        extract_dir = path.parent / (folder_name or f"{path.name}_extraido")
        try:
            unpack_archive(path, extract_dir)
            source_str = str(path)
            path.unlink()
            db.log_move(
                filename=path.name,
                source=source_str,
                destination=str(extract_dir),
                category="desempaquetado",
            )
            return {
                "filename": path.name,
                "source": source_str,
                "destination": str(extract_dir),
                "category": "desempaquetado",
            }
        except Exception as exc:
            logger.warning("no se pudo desempaquetar %s, continuando clasificacion normal: %s", path.name, exc)
            if extract_dir.exists() and extract_dir.is_dir():
                try:
                    if not any(extract_dir.iterdir()):
                        extract_dir.rmdir()
                except OSError:
                    pass

    category, relative_folder, rename_pattern = resolve_destination_folder(path)

    dest_dir = safe_destination_dir(relative_folder)
    if dest_dir is None:
        logger.warning("destino invalido %r para %s; no se mueve", relative_folder, path.name)
        return None

    if dest_dir.resolve() == path.parent.resolve():
        return None

    topic_name = category.split(": ", 1)[1] if category.startswith("tema: ") else None
    if rename_pattern:
        dest_filename = format_rename_pattern(rename_pattern, path, category, topic_name)
    else:
        dest_filename = path.name

    with _move_lock:
        destination = dest_dir / dest_filename
        if destination.exists():
            if destination.stat().st_size == path.stat().st_size and calculate_sha256(destination) == calculate_sha256(path):
                action = db.get_setting("duplicate_action", "suffix")
                if action == "delete_source":
                    try:
                        path.unlink()
                        logger.info("Eliminado duplicado en origen: %s (ya existe identico en destino)", path.name)
                    except OSError as exc:
                        logger.error("error eliminando duplicado %s: %s", path.name, exc)
                    return None
                elif action == "skip":
                    logger.info("Omitido movimiento: %s ya existe e identico en destino", path.name)
                    return None

            destination = _unique_destination(dest_dir, dest_filename)

        if destination.resolve() == path.resolve():
            return None

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            source_str = str(path)
            shutil.move(source_str, str(destination))
        except OSError as exc:
            logger.error("no se pudo mover %s: %s", path.name, exc)
            return None

    db.log_move(
        filename=path.name,
        source=source_str,
        destination=str(destination),
        category=category,
    )
    return {
        "filename": path.name,
        "source": source_str,
        "destination": str(destination),
        "category": category,
    }


def organize_directory(directory: Path) -> list[dict]:
    """Organiza de golpe todos los archivos y carpetas ya existentes en un directorio
    (usado por 'Organizar Ahora')."""
    moved = []
    if not directory.exists():
        return moved
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_file():
            if is_temporary_download_file(entry) or is_file_in_use(entry):
                continue
            try:
                if entry.stat().st_size == 0:
                    continue
            except OSError:
                continue
            result = organize_file(entry)
            if result:
                moved.append(result)
        elif entry.is_dir():
            if is_destination_or_reserved_dir(entry) or is_file_in_use(entry):
                continue
            result = organize_folder(entry)
            if result:
                moved.append(result)
    return moved


def undo_move(move_id: int) -> tuple[dict | None, str | None]:
    """Devuelve un archivo del historial a su carpeta de origen.
    Retorna (datos_movimiento, mensaje_error)."""
    move = db.get_move(move_id)
    if not move:
        return None, "movimiento no encontrado en la base de datos"
    if move["undone_at"]:
        return None, "este movimiento ya fue deshecho anteriormente"

    dest_path = Path(move["destination"])
    orig_path = Path(move["source"])

    if not dest_path.exists():
        return None, f"el archivo ya no esta en su carpeta de destino ({dest_path.name})"

    orig_dir = orig_path.parent
    try:
        orig_dir.mkdir(parents=True, exist_ok=True)
        final_orig = _unique_destination(orig_dir, orig_path.name)
        shutil.move(str(dest_path), str(final_orig))
    except OSError as exc:
        logger.error("fallo al deshacer el movimiento de %s: %s", dest_path.name, exc)
        return None, f"error del sistema de archivos: {exc}"

    db.mark_move_undone(move_id)
    return {
        "filename": dest_path.name,
        "source": move["destination"],
        "destination": str(final_orig),
    }, None


def run_maintenance_cleanup() -> list[dict]:
    """Recorre las rutas de las reglas de mantenimiento activas y elimina
    los archivos cuya antigüedad supera la indicada.
    Retorna la lista de archivos eliminados."""
    deleted_files = []
    # 1. Obtener todas las reglas activas
    rules = db.list_maintenance_rules()
    active_rules = [r for r in rules if r.get("active", 1)]

    current_time = time.time()

    for rule in active_rules:
        folder_str = rule.get("folder")
        max_age_days = rule.get("max_age_days")
        if not folder_str or max_age_days is None:
            continue

        # 2. Validar ruta
        resolved_dir = resolve_safe_path(folder_str)
        if not resolved_dir or not resolved_dir.exists() or not resolved_dir.is_dir():
            logger.warning("Ruta de mantenimiento invalida o insegura: %s", folder_str)
            continue

        # 3. Recorrer de forma recursiva
        for root, dirs, files in os.walk(resolved_dir):
            for file in files:
                file_path = Path(root) / file
                # Segunda validacion de seguridad para cada archivo recorrido (evitar escape por enlaces simbolicos o similares)
                resolved_file_path = resolve_safe_path(str(file_path))
                if not resolved_file_path:
                    continue
                
                try:
                    stat_info = resolved_file_path.stat()
                    # Comprobar la edad
                    age_seconds = current_time - stat_info.st_mtime
                    age_days = age_seconds / 86400
                    if age_days > max_age_days:
                        # Eliminar el archivo
                        resolved_file_path.unlink()
                        # Registrar en moves_log
                        db.log_move(
                            filename=resolved_file_path.name,
                            source=str(resolved_file_path),
                            destination="DELETED",
                            category="mantenimiento"
                        )
                        deleted_files.append({
                            "filename": resolved_file_path.name,
                            "path": str(resolved_file_path),
                            "age_days": round(age_days, 2)
                        })
                        logger.info("Archivo de mantenimiento eliminado: %s (edad: %.2f dias)", resolved_file_path, age_days)
                except OSError as exc:
                    logger.error("Error al procesar/eliminar %s en mantenimiento: %s", file_path, exc)

    return deleted_files

