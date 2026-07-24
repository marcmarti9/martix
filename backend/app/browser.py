"""Navegacion segura por el sistema de archivos para la interfaz tipo
'explorador de archivos': arbol de carpetas (categorias + Temas) y listado
del contenido real de una carpeta. Solo permite mirar dentro de la carpeta
personal del usuario (o la de Descargas, si esta fuera de la carpeta
personal) para no exponer el resto del disco."""

from datetime import datetime
from pathlib import Path

from app import db
from config.settings import DOWNLOADS_DIR, HOME_DIR, load_categories


def _path_to_key(resolved: Path) -> str:
    """Convierte una ruta absoluta en algo relativo a la carpeta personal
    cuando es posible (mas legible y portable), o en la ruta absoluta si
    queda fuera (p.ej. una carpeta de Descargas personalizada)."""
    try:
        return str(resolved.relative_to(HOME_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return str(resolved)


def resolve_safe_path(raw_path: str) -> Path | None:
    """Resuelve un 'path' recibido de la interfaz a una ruta absoluta real,
    solo si cae dentro de la carpeta personal o de Descargas. Devuelve None
    si intenta escaparse (p.ej. "../../etc")."""
    raw_path = (raw_path or "").strip()
    home_resolved = HOME_DIR.resolve()
    downloads_resolved = DOWNLOADS_DIR.resolve()

    candidate = Path(raw_path) if raw_path else HOME_DIR
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (HOME_DIR / raw_path).resolve()

    for root in (home_resolved, downloads_resolved):
        if resolved == root or root in resolved.parents:
            return resolved
    return None


def list_directory(resolved: Path) -> list[dict]:
    """Lista una carpeta ocultando lo que Martix nunca debe exponer.

    El explorador es un mapa de la carpeta personal, y devolverlo entero
    significaba listar ~/.ssh, ~/.aws o ~/.gnupg: los nombres de archivo por si
    solos ya dicen a un atacante donde estan las claves.
    """
    from app.security import is_protected_path

    entries = []
    for entry in sorted(resolved.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        if is_protected_path(entry):
            continue
        try:
            # No seguir enlaces: su tamano y fecha son los del destino, que
            # puede estar en cualquier parte del sistema.
            stat = entry.stat()
            is_dir = entry.is_dir()
        except OSError:
            continue
        entries.append({
            "name": entry.name,
            "is_dir": is_dir,
            "path": _path_to_key(entry.resolve()) if is_dir else None,
            "size": stat.st_size if entry.is_file() else None,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "ext": entry.suffix.lower().lstrip(".") if entry.is_file() else "",
        })
    return entries


def build_tree() -> list[dict]:
    """Arbol para la barra lateral: Descargas + categorias base + tus Temas."""
    categories = load_categories()["categories"]

    tree = [{
        "key": "downloads",
        "label": "Descargas",
        "icon": "downloads",
        "path": _path_to_key(DOWNLOADS_DIR.resolve()),
    }]

    for cat_key, cat in categories.items():
        tree.append({
            "key": cat_key,
            "label": cat.get("label", cat_key.capitalize()),
            "icon": cat.get("icon", "folder"),
            "path": cat["folder"],
        })

    for topic in db.list_topics():
        tree.append({
            "key": f"topic-{topic['id']}",
            "label": topic["name"],
            "icon": "topic",
            "path": topic["destination"],
        })

    return tree
