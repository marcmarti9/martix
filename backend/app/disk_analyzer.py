"""Analizador de uso de disco para Martix.
Escanea de forma ultra-rápida carpetas y directorios, calcula tamaños acumulados,
conteo de archivos/carpetas, desglose por extensiones y datos para treemap visual.
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.browser import _path_to_key, resolve_safe_path
from config.settings import DOWNLOADS_DIR, HOME_DIR, load_categories


EXTENSION_CATEGORIES = {
    # Imagenes
    "png": ("Imagen PNG", "#3b82f6"),
    "jpg": ("Imagen JPEG", "#3b82f6"),
    "jpeg": ("Imagen JPEG", "#3b82f6"),
    "gif": ("GIF Animado", "#3b82f6"),
    "webp": ("Imagen WebP", "#3b82f6"),
    "svg": ("Vectorial SVG", "#3b82f6"),
    "bmp": ("Imagen BMP", "#3b82f6"),
    "ico": ("Icono ICO", "#3b82f6"),
    "tiff": ("Imagen TIFF", "#3b82f6"),
    # Video
    "mp4": ("Vídeo MP4", "#10b981"),
    "mkv": ("Vídeo MKV", "#10b981"),
    "avi": ("Vídeo AVI", "#10b981"),
    "mov": ("Vídeo QuickTime", "#10b981"),
    "wmv": ("Vídeo WMV", "#10b981"),
    "webm": ("Vídeo WebM", "#10b981"),
    "flv": ("Vídeo FLV", "#10b981"),
    # Audio
    "mp3": ("Audio MP3", "#8b5cf6"),
    "wav": ("Audio WAV", "#8b5cf6"),
    "flac": ("Audio FLAC", "#8b5cf6"),
    "aac": ("Audio AAC", "#8b5cf6"),
    "ogg": ("Audio OGG", "#8b5cf6"),
    "m4a": ("Audio M4A", "#8b5cf6"),
    # Documentos
    "pdf": ("Documento PDF", "#ec4899"),
    "docx": ("Documento Word", "#ec4899"),
    "doc": ("Documento Word", "#ec4899"),
    "xlsx": ("Hoja de Cálculo Excel", "#ec4899"),
    "xls": ("Hoja de Cálculo Excel", "#ec4899"),
    "pptx": ("Presentación PowerPoint", "#ec4899"),
    "ppt": ("Presentación PowerPoint", "#ec4899"),
    "txt": ("Texto Plano", "#ec4899"),
    "csv": ("Archivo CSV", "#ec4899"),
    "odt": ("Documento ODT", "#ec4899"),
    "md": ("Markdown", "#ec4899"),
    # Archivos comprimidos
    "zip": ("Archivo ZIP", "#f59e0b"),
    "tar": ("Archivo TAR", "#f59e0b"),
    "gz": ("Comprimido GZ", "#f59e0b"),
    "7z": ("Archivo 7-Zip", "#f59e0b"),
    "rar": ("Archivo RAR", "#f59e0b"),
    "iso": ("Imagen ISO", "#f59e0b"),
    "bz2": ("Comprimido BZ2", "#f59e0b"),
    # Ejecutables y codigo
    "exe": ("Ejecutable Windows", "#06b6d4"),
    "app": ("Aplicación macOS", "#06b6d4"),
    "sh": ("Script Bash", "#06b6d4"),
    "py": ("Código Python", "#06b6d4"),
    "js": ("Código JavaScript", "#06b6d4"),
    "ts": ("Código TypeScript", "#06b6d4"),
    "html": ("Página HTML", "#06b6d4"),
    "css": ("Estilo CSS", "#06b6d4"),
    "json": ("Datos JSON", "#06b6d4"),
    "cpp": ("Código C++", "#06b6d4"),
    "c": ("Código C", "#06b6d4"),
    "java": ("Código Java", "#06b6d4"),
    "dll": ("Librería DLL", "#06b6d4"),
    "so": ("Librería Compartida SO", "#06b6d4"),
    # Datos y sistema
    "db": ("Base de Datos SQLite/DB", "#64748b"),
    "sqlite": ("Base de Datos SQLite", "#64748b"),
    "log": ("Archivo de Registro Log", "#64748b"),
    "tmp": ("Archivo Temporal", "#64748b"),
}


def get_extension_info(ext: str) -> Tuple[str, str]:
    ext_clean = ext.lower().lstrip(".")
    if not ext_clean:
        return "(Sin extensión)", "#94a3b8"
    if ext_clean in EXTENSION_CATEGORIES:
        return EXTENSION_CATEGORIES[ext_clean]
    return f"Archivo .{ext_clean.upper()}", "#94a3b8"


def format_bytes(bytes_num: int) -> str:
    if bytes_num < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    val = float(bytes_num)
    unit_idx = 0
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1
    if unit_idx == 0:
        return f"{int(val)} B"
    return f"{val:.1f} {units[unit_idx]}"


def get_available_drives() -> List[Dict[str, str]]:
    """Devuelve las ubicaciones / carpetas disponibles para escanear."""
    drives = [
        {
            "name": "Carpeta Personal (~)",
            "path": _path_to_key(HOME_DIR.resolve()),
            "type": "home"
        },
        {
            "name": "Descargas",
            "path": _path_to_key(DOWNLOADS_DIR.resolve()),
            "type": "downloads"
        }
    ]

    try:
        categories = load_categories().get("categories", {})
        for cat_key, cat in categories.items():
            folder_str = cat.get("folder")
            if folder_str:
                resolved = resolve_safe_path(folder_str)
                if resolved and resolved.exists():
                    drives.append({
                        "name": cat.get("label", cat_key.capitalize()),
                        "path": _path_to_key(resolved),
                        "type": "category"
                    })
    except Exception:
        pass

    return drives


def scan_disk_usage(root_path: Path, max_depth: int = 6) -> Dict[str, Any]:
    """Escanea recursivamente root_path produciendo arbol de carpetas estilo WizTree,
    estadisticas de uso, desglose de extensiones y lista para Treemap visual.
    """
    start_time = time.perf_counter()

    root_resolved = root_path.resolve()
    if not root_resolved.exists():
        raise ValueError(f"La ruta no existe: {root_path}")

    # Informacion global del disco
    total_space, used_space, free_space = 0, 0, 0
    try:
        usage = shutil.disk_usage(root_resolved)
        total_space = usage.total
        used_space = usage.used
        free_space = usage.free
    except OSError:
        pass

    extension_map: Dict[str, Dict[str, Any]] = {}
    treemap_items: List[Dict[str, Any]] = []

    def _scan_node(current_path: Path, current_depth: int) -> Dict[str, Any]:
        node_name = current_path.name or str(current_path)
        path_key = _path_to_key(current_path)
        
        node_size = 0
        files_count = 0
        folders_count = 0
        latest_mtime = 0.0

        children = []
        direct_files = []

        try:
            entries = list(os.scandir(current_path))
        except OSError:
            entries = []

        for entry in entries:
            try:
                stat = entry.stat(follow_symlinks=False)
                mtime = stat.st_mtime
                if mtime > latest_mtime:
                    latest_mtime = mtime
            except OSError:
                continue

            if entry.is_dir(follow_symlinks=False):
                folders_count += 1
                child_path = Path(entry.path)
                child_node = _scan_node(child_path, current_depth + 1)
                
                node_size += child_node["size"]
                files_count += child_node["files_count"]
                folders_count += child_node["folders_count"]
                if child_node["mtime_timestamp"] > latest_mtime:
                    latest_mtime = child_node["mtime_timestamp"]
                
                # Guardar solo subhijos si no excedemos max_depth
                if current_depth < max_depth:
                    children.append(child_node)
            elif entry.is_file(follow_symlinks=False):
                files_count += 1
                f_size = stat.st_size
                node_size += f_size

                ext = Path(entry.name).suffix.lower().lstrip(".")
                ext_key = f".{ext}" if ext else "(Sin extensión)"
                type_name, color = get_extension_info(ext)

                if ext_key not in extension_map:
                    extension_map[ext_key] = {
                        "extension": ext_key,
                        "type_name": type_name,
                        "color": color,
                        "size": 0,
                        "count": 0,
                    }
                extension_map[ext_key]["size"] += f_size
                extension_map[ext_key]["count"] += 1

                # Guardar archivos significativos para el Treemap
                if f_size > 512 * 1024:  # > 512 KB
                    treemap_items.append({
                        "name": entry.name,
                        "path": _path_to_key(Path(entry.path)),
                        "size": f_size,
                        "size_formatted": format_bytes(f_size),
                        "is_dir": False,
                        "extension": ext_key,
                        "color": color,
                        "type_name": type_name
                    })

                if current_depth < max_depth and f_size > 10 * 1024 * 1024: # Mostrar archivos > 10MB en el arbol
                    direct_files.append({
                        "name": entry.name,
                        "path": _path_to_key(Path(entry.path)),
                        "is_dir": False,
                        "size": f_size,
                        "size_formatted": format_bytes(f_size),
                        "percent_of_parent": 0.0,
                        "items_count": 1,
                        "files_count": 1,
                        "folders_count": 0,
                        "mtime": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                        "mtime_timestamp": mtime,
                        "children": []
                    })

        # Ordenar hijos por tamaño descendente
        children.sort(key=lambda x: x["size"], reverse=True)
        direct_files.sort(key=lambda x: x["size"], reverse=True)

        # Calcular porcentaje respecto al padre
        for c in children:
            c["percent_of_parent"] = round((c["size"] / node_size * 100), 1) if node_size > 0 else 0.0
            # Si el hijo es un directorio grande, añadirlo como bloque de treemap
            if c["size"] > 2 * 1024 * 1024:  # > 2 MB
                type_name, color = "Carpeta", "#3b82f6"
                treemap_items.append({
                    "name": c["name"],
                    "path": c["path"],
                    "size": c["size"],
                    "size_formatted": format_bytes(c["size"]),
                    "is_dir": True,
                    "extension": "Folder",
                    "color": color,
                    "type_name": "Carpeta"
                })

        for df in direct_files:
            df["percent_of_parent"] = round((df["size"] / node_size * 100), 1) if node_size > 0 else 0.0

        # Combinar subcarpetas y archivos directos grandes en la vista de arbol
        all_children = children + direct_files
        all_children.sort(key=lambda x: x["size"], reverse=True)

        mtime_str = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M") if latest_mtime > 0 else ""

        return {
            "name": node_name,
            "path": path_key,
            "is_dir": True,
            "size": node_size,
            "size_formatted": format_bytes(node_size),
            "percent_of_parent": 100.0,
            "items_count": files_count + folders_count,
            "files_count": files_count,
            "folders_count": folders_count,
            "mtime": mtime_str,
            "mtime_timestamp": latest_mtime,
            "children": all_children
        }

    tree_root = _scan_node(root_resolved, current_depth=0)
    elapsed_seconds = round(time.perf_counter() - start_time, 3)

    # Preparar resumen de extensiones ordenado por tamaño
    total_scanned_size = tree_root["size"]
    extensions_list = list(extension_map.values())
    extensions_list.sort(key=lambda x: x["size"], reverse=True)

    for item in extensions_list:
        item["size_formatted"] = format_bytes(item["size"])
        item["percent"] = round((item["size"] / total_scanned_size * 100), 1) if total_scanned_size > 0 else 0.0

    # Limitar elementos de treemap a los 150 elementos mas grandes para rendimiento optimo del canvas
    treemap_items.sort(key=lambda x: x["size"], reverse=True)
    top_treemap_items = treemap_items[:150]

    return {
        "scan_path": _path_to_key(root_resolved),
        "scan_time_seconds": elapsed_seconds,
        "disk_info": {
            "total_space": total_space,
            "total_space_formatted": format_bytes(total_space),
            "used_space": used_space,
            "used_space_formatted": format_bytes(used_space),
            "used_percent": round((used_space / total_space * 100), 1) if total_space > 0 else 0,
            "free_space": free_space,
            "free_space_formatted": format_bytes(free_space),
            "free_percent": round((free_space / total_space * 100), 1) if total_space > 0 else 0,
        },
        "tree": tree_root,
        "extensions": extensions_list,
        "treemap": top_treemap_items
    }
