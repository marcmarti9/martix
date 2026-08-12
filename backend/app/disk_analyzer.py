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


# Paleta de piedra/arena. El mapa de uso no debe ser un arcoíris de SaaS.
_STONE = {
    "image": "#a89880",
    "video": "#6f675c",
    "audio": "#8d7a68",
    "doc": "#b7a48c",
    "archive": "#9a8b76",
    "binary": "#5c564e",
    "code": "#7d766c",
    "data": "#8a8378",
}

EXTENSION_CATEGORIES = {
    "png": ("Imagen PNG", _STONE["image"]),
    "jpg": ("Imagen JPEG", _STONE["image"]),
    "jpeg": ("Imagen JPEG", _STONE["image"]),
    "gif": ("GIF Animado", _STONE["image"]),
    "webp": ("Imagen WebP", _STONE["image"]),
    "svg": ("Vectorial SVG", _STONE["image"]),
    "bmp": ("Imagen BMP", _STONE["image"]),
    "ico": ("Icono ICO", _STONE["image"]),
    "tiff": ("Imagen TIFF", _STONE["image"]),
    "heic": ("Imagen HEIC", _STONE["image"]),
    "raw": ("Imagen RAW", _STONE["image"]),
    "psd": ("Proyecto Photoshop", _STONE["image"]),
    "mp4": ("Vídeo MP4", _STONE["video"]),
    "mkv": ("Vídeo MKV", _STONE["video"]),
    "avi": ("Vídeo AVI", _STONE["video"]),
    "mov": ("Vídeo QuickTime", _STONE["video"]),
    "wmv": ("Vídeo WMV", _STONE["video"]),
    "webm": ("Vídeo WebM", _STONE["video"]),
    "flv": ("Vídeo FLV", _STONE["video"]),
    "m4v": ("Vídeo M4V", _STONE["video"]),
    "mp3": ("Audio MP3", _STONE["audio"]),
    "wav": ("Audio WAV", _STONE["audio"]),
    "flac": ("Audio FLAC", _STONE["audio"]),
    "aac": ("Audio AAC", _STONE["audio"]),
    "ogg": ("Audio OGG", _STONE["audio"]),
    "m4a": ("Audio M4A", _STONE["audio"]),
    "wma": ("Audio WMA", _STONE["audio"]),
    "opus": ("Audio OPUS", _STONE["audio"]),
    "pdf": ("Documento PDF", _STONE["doc"]),
    "docx": ("Documento Word", _STONE["doc"]),
    "doc": ("Documento Word", _STONE["doc"]),
    "xlsx": ("Hoja de Cálculo Excel", _STONE["doc"]),
    "xls": ("Hoja de Cálculo Excel", _STONE["doc"]),
    "pptx": ("Presentación PowerPoint", _STONE["doc"]),
    "ppt": ("Presentación PowerPoint", _STONE["doc"]),
    "txt": ("Texto Plano", _STONE["doc"]),
    "csv": ("Archivo CSV", _STONE["doc"]),
    "odt": ("Documento ODT", _STONE["doc"]),
    "md": ("Markdown", _STONE["doc"]),
    "epub": ("Libro EPUB", _STONE["doc"]),
    "zip": ("Archivo ZIP", _STONE["archive"]),
    "tar": ("Archivo TAR", _STONE["archive"]),
    "gz": ("Comprimido GZ", _STONE["archive"]),
    "7z": ("Archivo 7-Zip", _STONE["archive"]),
    "rar": ("Archivo RAR", _STONE["archive"]),
    "iso": ("Imagen ISO", _STONE["archive"]),
    "bz2": ("Comprimido BZ2", _STONE["archive"]),
    "xz": ("Comprimido XZ", _STONE["archive"]),
    "tgz": ("Comprimido TGZ", _STONE["archive"]),
    "deb": ("Paquete DEB", _STONE["archive"]),
    "rpm": ("Paquete RPM", _STONE["archive"]),
    "exe": ("Ejecutable Windows", _STONE["binary"]),
    "app": ("Aplicación macOS", _STONE["binary"]),
    "appimage": ("Aplicación AppImage", _STONE["binary"]),
    "dll": ("Librería DLL", _STONE["binary"]),
    "so": ("Librería Compartida SO", _STONE["binary"]),
    "dylib": ("Librería dylib macOS", _STONE["binary"]),
    "gguf": ("Modelo IA GGUF", _STONE["binary"]),
    "safetensors": ("Modelo IA SafeTensors", _STONE["binary"]),
    "bin": ("Binario / Datos", _STONE["binary"]),
    "jar": ("Archivo Java JAR", _STONE["binary"]),
    "rlib": ("Librería Rust RLIB", _STONE["binary"]),
    "a": ("Librería Estática", _STONE["binary"]),
    "o": ("Objeto Compilado", _STONE["binary"]),
    "node": ("Módulo Node.js Native", _STONE["binary"]),
    "part": ("Descarga Parcial", _STONE["data"]),
    "dill": ("Objeto Serializado Python", _STONE["code"]),
    "sh": ("Script Bash", _STONE["code"]),
    "py": ("Código Python", _STONE["code"]),
    "js": ("Código JavaScript", _STONE["code"]),
    "ts": ("Código TypeScript", _STONE["code"]),
    "jsx": ("Componente React", _STONE["code"]),
    "tsx": ("Componente React TS", _STONE["code"]),
    "html": ("Página HTML", _STONE["code"]),
    "css": ("Estilo CSS", _STONE["code"]),
    "json": ("Datos JSON", _STONE["code"]),
    "cpp": ("Código C++", _STONE["code"]),
    "c": ("Código C", _STONE["code"]),
    "rs": ("Código Rust", _STONE["code"]),
    "go": ("Código Go", _STONE["code"]),
    "java": ("Código Java", _STONE["code"]),
    "db": ("Base de Datos SQLite/DB", _STONE["data"]),
    "sqlite": ("Base de Datos SQLite", _STONE["data"]),
    "log": ("Archivo de Registro Log", _STONE["data"]),
    "tmp": ("Archivo Temporal", _STONE["data"]),
}


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convierte valores HSL (0-360, 0-1, 0-1) a formato Hex (#rrggbb)."""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    ri, gi, bi = int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)
    return f"#{ri:02x}{gi:02x}{bi:02x}"


_EXT_INFO_CACHE: Dict[str, Tuple[str, str]] = {}


def get_extension_info(ext: str) -> Tuple[str, str]:
    ext_clean = ext.lower().strip().lstrip(".")
    if not ext_clean:
        return "(Sin extensión)", "#64748b"
    cached = _EXT_INFO_CACHE.get(ext_clean)
    if cached is not None:
        return cached
    if ext_clean in EXTENSION_CATEGORIES:
        res = EXTENSION_CATEGORIES[ext_clean]
    else:
        # Generar color HSL determinista para cualquier extensión no listada
        h = 32 + (sum(ord(ch) for ch in ext_clean) * 13 % 28)
        color_hex = _hsl_to_hex(h, 0.12, 0.48)
        res = (f"Archivo .{ext_clean.upper()}", color_hex)
    _EXT_INFO_CACHE[ext_clean] = res
    return res


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


# Limites del escaneo. Sin ellos, analizar "~" recorria el arbol entero de
# forma recursiva dentro de la peticion HTTP: minutos de bloqueo y riesgo de
# RecursionError (el limite de Python son ~1000 marcos) en arboles anidados.
MAX_SCAN_DEPTH = 40          # profundidad real de recursion
DEFAULT_TIME_BUDGET = 90.0   # segundos antes de devolver un resultado parcial
MAX_TREEMAP_CANDIDATES = 20_000


def scan_disk_usage(root_path: Path, max_depth: int = 6,
                    time_budget: float = DEFAULT_TIME_BUDGET) -> Dict[str, Any]:
    """Escanea recursivamente root_path produciendo arbol de carpetas estilo WizTree,
    estadisticas de uso, desglose de extensiones y lista para Treemap visual.

    'max_depth' controla hasta que nivel se CONSTRUYE el arbol para la interfaz;
    los tamanos se siguen sumando mas abajo, pero con un acumulador iterativo
    que no gasta pila ni memoria. 'time_budget' acota el tiempo total: si se
    agota, se devuelve lo obtenido con truncated=True.
    """
    start_time = time.perf_counter()
    deadline = start_time + max(1.0, time_budget)
    truncated = False

    root_resolved = root_path.resolve()
    if not root_resolved.exists():
        raise ValueError(f"La ruta no existe: {root_path}")
    if not root_resolved.is_dir():
        raise ValueError(f"La ruta no es una carpeta: {root_path}")

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

    def _aggregate_subtree(start: Path) -> tuple[int, int, int, float]:
        """Suma tamanos por debajo de max_depth sin construir nodos ni recursion.

        Devuelve (bytes, archivos, carpetas, mtime_mas_reciente). Tambien
        alimenta el desglose por extensiones para que las estadisticas globales
        sigan siendo exactas.
        """
        nonlocal truncated
        total_size = files = folders = 0
        latest = 0.0
        stack = [start]
        while stack:
            if time.perf_counter() > deadline:
                truncated = True
                break
            current = stack.pop()
            try:
                entries = list(os.scandir(current))
            except OSError:
                continue
            for entry in entries:
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if st.st_mtime > latest:
                    latest = st.st_mtime
                if entry.is_dir(follow_symlinks=False):
                    folders += 1
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    files += 1
                    total_size += st.st_size
                    _record_extension(entry.name, st.st_size)
        return total_size, files, folders, latest

    def _get_ext_clean(filename: str) -> str:
        if "." in filename and not filename.startswith("."):
            return filename.rsplit(".", 1)[-1].lower()
        return ""

    def _record_extension(name: str, size: int) -> None:
        ext = _get_ext_clean(name)
        ext_key = f".{ext}" if ext else "(Sin extensión)"
        bucket = extension_map.get(ext_key)
        if bucket is None:
            type_name, color = get_extension_info(ext)
            bucket = extension_map[ext_key] = {
                "extension": ext_key, "type_name": type_name,
                "color": color, "size": 0, "count": 0,
            }
        bucket["size"] += size
        bucket["count"] += 1

    def _scan_node(current_path: Path, current_depth: int) -> Dict[str, Any]:
        nonlocal truncated
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
            if time.perf_counter() > deadline:
                truncated = True
                break
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

                # Por debajo del nivel que la interfaz muestra, o si el arbol es
                # patologicamente profundo, se pasa al acumulador iterativo.
                if current_depth >= max_depth or current_depth >= MAX_SCAN_DEPTH:
                    sub_size, sub_files, sub_folders, sub_mtime = _aggregate_subtree(child_path)
                    node_size += sub_size
                    files_count += sub_files
                    folders_count += sub_folders
                    latest_mtime = max(latest_mtime, sub_mtime)
                    continue

                child_node = _scan_node(child_path, current_depth + 1)

                node_size += child_node["size"]
                files_count += child_node["files_count"]
                folders_count += child_node["folders_count"]
                if child_node["mtime_timestamp"] > latest_mtime:
                    latest_mtime = child_node["mtime_timestamp"]

                children.append(child_node)
            elif entry.is_file(follow_symlinks=False):
                files_count += 1
                f_size = stat.st_size
                node_size += f_size

                ext = _get_ext_clean(entry.name)
                ext_key = f".{ext}" if ext else "(Sin extensión)"
                type_name, color = get_extension_info(ext)
                _record_extension(entry.name, f_size)

                # Guardar archivos significativos para el Treemap. Se acota la
                # lista: en "~" completo se acumulaban cientos de miles de
                # entradas en memoria solo para quedarse con las 150 mayores.
                if f_size > 512 * 1024 and len(treemap_items) < MAX_TREEMAP_CANDIDATES:
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
            if c["size"] > 2 * 1024 * 1024 and len(treemap_items) < MAX_TREEMAP_CANDIDATES:
                type_name, color = "Carpeta", "#8a8175"
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
        # La interfaz avisa al usuario de que el resultado es parcial en vez de
        # presentar cifras incompletas como si fueran definitivas.
        "truncated": truncated,
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
