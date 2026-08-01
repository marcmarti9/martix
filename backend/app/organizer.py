"""Decide el destino final de un archivo (reglas del usuario primero, si no
el clasificador inteligente), lo mueve de forma segura sin pisar archivos
con el mismo nombre, y permite deshacer un movimiento del historial."""

import datetime
import hashlib
import json
import logging
import ntpath
import os
import re
import shutil
import tarfile
import threading
import time
import zipfile
from pathlib import Path

from app import db, trash
from app.browser import resolve_safe_path
from app.classifier import (
    classify,
    content_is_extractable,
    extract_metadata,
    normalize,
    _extract_content,
)
from app.security import (
    PROTECTED_PATHS,
    RESERVED_DIR_NAMES,
    is_protected_path,
    safe_destination_dir,
)
from config.settings import DOWNLOADS_DIR, HOME_DIR, IGNORED_SUFFIXES, is_temporary_download_file, is_file_in_use

logger = logging.getLogger("martix.organizer")


def _portable_path(path: Path) -> str:
    """Use slash-separated paths in JSON responses on every platform."""
    return str(path).replace("\\", "/")


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
    """Carpetas que Martix considera 'suyas': Descargas, las carpetas de las
    categorias, los destinos de los Temas y las carpetas vigiladas."""
    dirs = set()
    dirs.add(DOWNLOADS_DIR.resolve())

    def _add(folder_str: str | None) -> None:
        if not folder_str:
            return
        resolved = safe_destination_dir(folder_str)
        if resolved and resolved.exists():
            dirs.add(resolved.resolve())

    try:
        from config.settings import load_categories
        for cat in load_categories()["categories"].values():
            _add(cat.get("folder"))
    except Exception:
        logger.debug("no se pudieron leer las categorias para el listado de carpetas", exc_info=True)
    try:
        for topic in db.list_topics():
            _add(topic.get("destination"))
    except Exception:
        logger.debug("no se pudieron leer los Temas para el listado de carpetas", exc_info=True)
    try:
        # Las carpetas VIGILADAS por el usuario tambien son intocables: sin
        # esto, Martix podia clasificar y mover la propia carpeta que estaba
        # vigilando, dejando la vigilancia apuntando a una ruta inexistente.
        for watched in db.list_watched_folders():
            if not watched.get("active", 1):
                continue
            raw = watched.get("folder_path")
            if raw:
                candidate = Path(raw)
                if candidate.exists():
                    dirs.add(candidate.resolve())
    except Exception:
        logger.debug("no se pudieron leer las carpetas vigiladas", exc_info=True)

    return list(dirs)


# get_default_scan_dirs() consulta la base de datos y el disco; durante un
# barrido se llama una vez por entrada. Se cachea unos segundos: cambia solo
# cuando el usuario toca sus Temas o carpetas vigiladas.
_SCAN_DIRS_TTL_SECONDS = 5.0
_scan_dirs_cache: tuple[float, list[Path]] | None = None
_scan_dirs_lock = threading.Lock()


def get_cached_scan_dirs() -> list[Path]:
    global _scan_dirs_cache
    with _scan_dirs_lock:
        now = time.monotonic()
        if _scan_dirs_cache is not None and now - _scan_dirs_cache[0] < _SCAN_DIRS_TTL_SECONDS:
            return _scan_dirs_cache[1]
        dirs = get_default_scan_dirs()
        _scan_dirs_cache = (now, dirs)
        return dirs


def invalidate_scan_dirs_cache() -> None:
    """Llamar tras anadir/quitar Temas o carpetas vigiladas."""
    global _scan_dirs_cache
    with _scan_dirs_lock:
        _scan_dirs_cache = None


# La busqueda de duplicados corre dentro de la peticion HTTP y hashea con
# SHA256. Sin topes, apuntarla a una carpeta enorme bloquea un worker de Flask
# durante horas.
MAX_DUPLICATE_FILES = 200_000
DUPLICATE_TIME_BUDGET = 120.0


def find_duplicates(directories: list[Path] | None = None,
                    time_budget: float = DUPLICATE_TIME_BUDGET) -> list[dict]:
    """Busca archivos duplicados agrupando por tamaño, luego fast-hash, y finalmente hash completo."""
    if directories is None:
        directories = get_default_scan_dirs()

    deadline = time.monotonic() + max(5.0, time_budget)

    files = []
    seen_paths = set()
    for root_dir in directories:
        if not root_dir.exists() or not root_dir.is_dir():
            continue
        for root, dirs, filenames in os.walk(root_dir):
            if time.monotonic() > deadline or len(files) >= MAX_DUPLICATE_FILES:
                logger.warning("busqueda de duplicados truncada por limite de tiempo o de archivos")
                break
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".") and not (Path(root) / d).is_symlink()
            ]
            for f in filenames:
                if f.startswith('.'):
                    continue
                if Path(f).suffix.lower() in IGNORED_SUFFIXES:
                    continue
                file_path = Path(root) / f
                if file_path.is_symlink():
                    # Un enlace y su destino no son "duplicados": borrarlos
                    # como tales romperia el original.
                    continue
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
        if time.monotonic() > deadline:
            logger.warning("fase de hash completo truncada por limite de tiempo")
            break
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



# Limites de descompresion. Sin ellos, un .zip de pocos KB descargado
# automaticamente puede expandirse a cientos de GB y llenar el disco
# (zip bomb), o crear millones de entradas hasta agotar los inodos.
MAX_UNPACKED_BYTES = 4 * 1024 * 1024 * 1024   # 4 GB de contenido total
MAX_UNPACKED_ENTRIES = 20_000                  # numero de archivos dentro
MAX_COMPRESSION_RATIO = 200                    # x veces el tamano del comprimido
UNPACK_FREE_SPACE_MARGIN = 512 * 1024 * 1024   # dejar siempre 512 MB libres


def _check_unpack_budget(archive_path: Path, extract_dir_abs: str,
                         total_uncompressed: int, entries: int) -> None:
    """Rechaza archivos comprimidos cuyo contenido no cabe o es desproporcionado."""
    if entries > MAX_UNPACKED_ENTRIES:
        raise ValueError(
            f"el comprimido contiene {entries} entradas (maximo {MAX_UNPACKED_ENTRIES})"
        )
    if total_uncompressed > MAX_UNPACKED_BYTES:
        raise ValueError(
            f"el contenido descomprimido ocuparia {total_uncompressed} bytes "
            f"(maximo {MAX_UNPACKED_BYTES})"
        )
    try:
        compressed = archive_path.stat().st_size
    except OSError:
        compressed = 0
    if compressed > 0 and total_uncompressed / compressed > MAX_COMPRESSION_RATIO:
        raise ValueError(
            f"ratio de compresion sospechoso (x{total_uncompressed / compressed:.0f}); "
            "posible zip bomb"
        )
    try:
        free = shutil.disk_usage(extract_dir_abs).free
        if total_uncompressed + UNPACK_FREE_SPACE_MARGIN > free:
            raise ValueError("no hay espacio libre suficiente para descomprimir")
    except OSError:
        pass


def _validate_member_name(name: str, extract_dir_abs: str, kind: str) -> str:
    """Valida el nombre de una entrada y devuelve su ruta absoluta de destino."""
    if not name or name.startswith("/") or name.startswith("\\") or ntpath.isabs(name):
        raise ValueError(f"Ruta absoluta detectada en archivo {kind}: {name}")
    if "\x00" in name:
        raise ValueError(f"Nombre invalido en archivo {kind}: {name!r}")
    member_path = os.path.abspath(os.path.join(extract_dir_abs, name))
    if not (member_path == extract_dir_abs or member_path.startswith(extract_dir_abs + os.sep)):
        raise ValueError(f"Zip-Slip detectado en archivo {kind}: {name}")
    return member_path


def unpack_archive(archive_path: Path, extract_dir: Path) -> None:
    """Desempaqueta un archivo comprimido de forma segura, validando Zip-Slip /
    Path Traversal, enlaces que escapan del directorio y bombas de compresion."""
    extract_dir_abs = os.path.abspath(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    name_lower = archive_path.name.lower()

    if zipfile.is_zipfile(archive_path) or name_lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            members = zf.infolist()
            total = 0
            for member in members:
                _validate_member_name(member.filename, extract_dir_abs, "zip")
                total += member.file_size
            _check_unpack_budget(archive_path, extract_dir_abs, total, len(members))
            zf.extractall(extract_dir_abs)
    elif tarfile.is_tarfile(archive_path) or name_lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".gz")):
        with tarfile.open(archive_path, "r:*") as tf:
            members = tf.getmembers()
            total = 0
            for member in members:
                member_path = _validate_member_name(member.name, extract_dir_abs, "tar")
                total += max(member.size, 0)
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
                # Dispositivos y FIFOs no tienen sentido en una descarga y son
                # una via clasica de abuso.
                if member.isdev():
                    raise ValueError(f"Entrada de dispositivo no permitida en tar: {member.name}")
            _check_unpack_budget(archive_path, extract_dir_abs, total, len(members))
            # filter="data" (Python 3.12+) descarta permisos peligrosos, setuid
            # y rutas absolutas tambien dentro de extractall.
            try:
                tf.extractall(extract_dir_abs, filter="data")
            except TypeError:  # Python < 3.12
                tf.extractall(extract_dir_abs)
    else:
        raise ValueError(f"Formato de archivo comprimido no soportado: {archive_path}")


# Marcador para "este dato no se ha podido obtener". Distinto de None y de "":
# si no se puede evaluar un campo, la condicion NO casa.
_UNAVAILABLE = object()

_METADATA_FIELDS = ("artist", "album", "title", "year", "camera", "exif_date")


class FileFacts:
    """Datos de un archivo calculados como mucho una vez.

    Evaluar varias condiciones sobre el mismo archivo repetia el trabajo caro:
    una regla con tres condiciones de contenido volvia a abrir y parsear el PDF
    tres veces.
    """

    __slots__ = ("path", "ext", "_cache")

    def __init__(self, path: Path, ext: str):
        self.path = path
        self.ext = ext
        self._cache: dict[str, object] = {}

    def _stat(self):
        if "stat" not in self._cache:
            try:
                self._cache["stat"] = self.path.stat()
            except OSError:
                self._cache["stat"] = _UNAVAILABLE
        return self._cache["stat"]

    def value_for(self, field: str):
        if field == "name":
            return self.path.name
        if field == "stem":
            return self.path.stem
        if field == "extension":
            return self.ext
        if field == "size_kb":
            st = self._stat()
            return _UNAVAILABLE if st is _UNAVAILABLE else st.st_size / 1024
        if field == "age_days":
            st = self._stat()
            return _UNAVAILABLE if st is _UNAVAILABLE else (time.time() - st.st_mtime) / 86400
        if field == "content":
            if "content" not in self._cache:
                # Si Martix no sabe leer esta extension el contenido es
                # DESCONOCIDO, no vacio: devolver "" hacia que
                # `content not_contains X` casase con todos los binarios.
                self._cache["content"] = (
                    _extract_content(self.path, self.ext)
                    if content_is_extractable(self.ext) else _UNAVAILABLE
                )
            return self._cache["content"]
        if field in _METADATA_FIELDS:
            if "meta" not in self._cache:
                self._cache["meta"] = extract_metadata(self.path)
            value = self._cache["meta"].get(field)
            return _UNAVAILABLE if value is None else value
        return _UNAVAILABLE


def _compare_numeric(actual, expected, op: str) -> bool | None:
    """Compara numericamente. None si alguno de los dos no es un numero."""
    try:
        a, b = float(actual), float(expected)
    except (ValueError, TypeError):
        return None
    return {
        "gt": a > b, ">": a > b,
        "lt": a < b, "<": a < b,
        "gte": a >= b, ">=": a >= b,
        "lte": a <= b, "<=": a <= b,
        "equals": a == b, "==": a == b,
    }.get(op)


def check_conditions(path: Path, ext: str, conditions_str: str | None,
                     facts: FileFacts | None = None) -> bool:
    """Evalua las condiciones de una regla en AND. Si un campo no se puede
    obtener, la regla no casa."""
    if not conditions_str:
        return True  # Si no hay condiciones adicionales, es un match directo
    try:
        conditions = json.loads(conditions_str)
    except Exception:
        return False
    if not isinstance(conditions, list):
        return False

    if facts is None:
        facts = FileFacts(path, ext)

    for cond in conditions:
        if not isinstance(cond, dict):
            return False
        field = cond.get("field")
        op = cond.get("operator")
        val = cond.get("value")
        if not field or not op:
            continue

        actual = facts.value_for(field)
        if actual is _UNAVAILABLE or actual is None:
            return False

        if op in ("gt", ">", "lt", "<", "gte", ">=", "lte", "<="):
            if _compare_numeric(actual, val, op) is not True:
                return False
        elif op in ("equals", "=="):
            numeric = _compare_numeric(actual, val, op)
            if numeric is None:
                if normalize(str(actual)) != normalize(str(val)):
                    return False
            elif not numeric:
                return False
        elif op == "contains":
            if not isinstance(actual, str) or normalize(val) not in normalize(actual):
                return False
        elif op == "not_contains":
            if not isinstance(actual, str) or normalize(val) in normalize(actual):
                return False
        elif op == "starts_with":
            if not isinstance(actual, str) or not normalize(actual).startswith(normalize(val)):
                return False
        elif op == "ends_with":
            if not isinstance(actual, str) or not normalize(actual).endswith(normalize(val)):
                return False
        else:
            # operador desconocido: no se puede afirmar que la regla case
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

    # Sanitizar el nombre del archivo final. Se hace ANTES de comprobar si ha
    # quedado vacio, para que un patron como "{ARTIST}/{TITLE}" no se cuele.
    new_name = re.sub(r'[\x00/\\:*?"<>|]', "_", new_name)

    # Los placeholders sin valor (un archivo sin tema, un mp3 sin etiquetas)
    # dejaban nombres invalidos: "{Topic}" -> "" -> `dest_dir / ""` es el
    # PROPIO directorio destino, y con extension quedaba ".pdf", un archivo
    # oculto y sin nombre. Si no queda nada util, se conserva el original.
    stem_candidate = Path(new_name).stem.strip(" .-_")
    if not stem_candidate:
        logger.info(
            "el patron de renombrado %r no produjo un nombre util para %s; se conserva el original",
            pattern, path.name,
        )
        return path.name

    new_name = new_name.strip(" .")

    # Si el patron no especifica la extension y el archivo original tiene una, se la anadimos
    if not Path(new_name).suffix and path.suffix:
        new_name += path.suffix

    # Limite de nombre de la mayoria de sistemas de archivos (255 bytes),
    # recortando el cuerpo y respetando la extension.
    if len(new_name.encode("utf-8", "ignore")) > 255:
        suffix = Path(new_name).suffix[:32]
        body = new_name[: len(new_name) - len(Path(new_name).suffix)]
        while len((body + suffix).encode("utf-8", "ignore")) > 255 and body:
            body = body[:-1]
        new_name = (body or "archivo") + suffix

    return new_name


def resolve_destination_folder(
    path: Path,
    rules: list[dict] | None = None,
    topics: list[dict] | None = None,
) -> tuple[str, str, str | None]:
    """Devuelve (categoria, carpeta_relativa_a_home, rename_pattern) para un archivo dado.

    'rules' y 'topics' permiten reutilizar los datos ya leidos durante un
    barrido completo en vez de consultar SQLite una vez por archivo.
    """
    ext = path.suffix.lower().lstrip(".")
    if rules is None:
        rules = db.list_rules()
    if topics is None:
        topics = db.list_topics()

    # Una sola cache de datos costosos para todas las reglas del archivo.
    facts = FileFacts(path, ext)

    for rule in rules:
        rule_ext = rule.get("extension")
        # Si la regla especifica una extension concreta (y no es wildcard *), debe coincidir
        if rule_ext and rule_ext != "*" and rule_ext != ext:
            continue
        # Comprobar condiciones (AND)
        if check_conditions(path, ext, rule.get("conditions"), facts=facts):
            return "regla personalizada", rule["destination"], rule.get("rename_pattern")

    # Clasificar con el categorizador inteligente
    result = classify(path, topics=topics)
    return result["category"], result["folder"], result.get("rename_pattern")


# El watcher lanza varios workers concurrentes (y el scheduler/API pueden
# organizar en paralelo a ellos), asi que elegir un nombre de destino libre
# y mover el archivo debe ser una seccion critica: sin este lock, dos hilos
# podrian ver el mismo destino como libre a la vez (check-then-act) y uno
# pisaria silenciosamente el archivo del otro con shutil.move.
_move_lock = threading.Lock()


# Files that are usually only useful during installation are never removed by
# default.  They become a review suggestion after they have been filed.  The
# explicit name check avoids treating every portable .exe as disposable.
_INSTALLER_EXTENSIONS = frozenset({
    "msi", "msix", "appx", "msu", "cab", "deb", "rpm", "appimage", "dmg", "pkg", "apk",
})
_INSTALLER_NAME_RE = re.compile(
    r"(?:^|[ _.-])(setup|install(?:er)?|update|upgrade|driver|runtime|redistributable)(?:$|[ _.-])",
    re.IGNORECASE,
)


def cleanup_reason_for(path: Path) -> str | None:
    """Return a human-readable cleanup hint for high-confidence candidates."""
    ext = path.suffix.lower().lstrip(".")
    if ext in _INSTALLER_EXTENSIONS:
        return "Parece un instalador; puedes eliminarlo cuando termines de instalarlo."
    if ext == "exe" and _INSTALLER_NAME_RE.search(path.stem):
        return "Parece un instalador de Windows; puedes eliminarlo cuando termines de instalarlo."
    return None


def _cleanup_mode() -> str:
    mode = str(db.get_setting("cleanup_mode", "notify") or "notify").lower()
    return mode if mode in {"notify", "direct"} else "notify"


def _register_cleanup_candidate(path: Path, category: str) -> dict | None:
    """Suggest or safely trash a cleanup candidate after a successful move."""
    reason = cleanup_reason_for(path)
    if not reason or not path.exists() or is_protected_path(path):
        return None

    suggestion = db.add_cleanup_suggestion(str(path), reason, category=category)
    if _cleanup_mode() != "direct":
        return {**suggestion, "action": "notify"}

    # Direct mode is an explicit user preference, but even then deletion is
    # recoverable: send the item to the native trash/quarantine, never unlink.
    try:
        outcome = trash.move_to_trash(path)
    except OSError as exc:
        logger.warning("no se pudo retirar automaticamente %s: %s", path, exc)
        return {**suggestion, "action": "notify", "error": str(exc)}

    resolved = db.resolve_cleanup_suggestion(int(suggestion["id"]), "deleted")
    return {
        **(resolved or suggestion),
        "action": "deleted",
        "trash_method": outcome["method"],
        "trash_id": outcome["entry_id"],
    }


def _iter_folder_files(root: Path, max_files: int | None = None) -> list[Path]:
    """Collect real files from a downloaded folder without following links.

    ``max_files`` is optional and is only used by callers that explicitly want
    a bounded preview. The real organizer does not silently stop at an
    arbitrary per-folder limit.
    """
    files: list[Path] = []
    try:
        for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and not (current_path / d).is_symlink()
                and not is_destination_or_reserved_dir(current_path / d)
            ]
            for name in sorted(names, key=str.lower):
                if name.startswith("."):
                    continue
                candidate = current_path / name
                if candidate.is_symlink() or not candidate.is_file():
                    continue
                files.append(candidate)
                if max_files is not None and len(files) >= max_files:
                    logger.warning("se alcanzo el limite de archivos al explorar %s", root)
                    return files
    except OSError as exc:
        logger.warning("no se pudo explorar %s: %s", root, exc)
    return files


def _iter_directory_file_candidates(
    directory: Path,
    max_files: int | None = None,
) -> tuple[list[Path], list[Path], bool]:
    """Return files to inspect, source folders, and whether a preview was cut.

    Destination folders are deliberately excluded so a second click cannot
    pull already-organized files back into another category. Downloaded
    folders are flattened only for inspection; their individual files still
    receive their own classification.
    """
    candidates: list[Path] = []
    source_dirs: list[Path] = []
    truncated = False
    try:
        entries = sorted(directory.iterdir(), key=lambda p: p.name.lower())
    except OSError as exc:
        logger.warning("no se pudo listar %s: %s", directory, exc)
        return candidates, source_dirs, False

    for entry in entries:
        if entry.name.startswith(".") or entry.is_symlink():
            continue
        if max_files is not None and len(candidates) >= max_files:
            truncated = True
            break
        if entry.is_file():
            candidates.append(entry)
            continue
        if not entry.is_dir() or is_destination_or_reserved_dir(entry):
            continue

        source_dirs.append(entry)
        remaining = None if max_files is None else max_files - len(candidates)
        nested = _iter_folder_files(entry, max_files=remaining)
        candidates.extend(nested)
        if remaining is not None and len(nested) >= remaining:
            truncated = True
            break

    return candidates, source_dirs, truncated


def _plan_skip(path: Path, reason: str, category: str = "skip") -> dict:
    return {
        "filename": path.name,
        "current_path": str(path),
        "would_move_to": None,
        "category": category,
        "status": "skipped",
        "reason": reason,
    }


def _build_file_plan(
    path: Path,
    rules: list[dict],
    topics: list[dict] | None = None,
) -> dict:
    """Classify one candidate without mutating the filesystem.

    The returned private planning fields are consumed by ``organize_file`` so
    the real run executes the same decision that the simulation displayed.
    """
    if is_temporary_download_file(path):
        return _plan_skip(path, "Descarga temporal o incompleta; se espera a que termine.", "temporary")
    if is_protected_path(path):
        return _plan_skip(path, "Ruta protegida; no se toca.", "protected")
    try:
        if path.stat().st_size == 0:
            return _plan_skip(path, "Archivo vacio; no se clasifica.", "empty")
    except OSError:
        return _plan_skip(path, "No se pudo leer el archivo.", "unreadable")
    if is_file_in_use(path):
        return _plan_skip(path, "El archivo esta en uso por otra aplicacion.", "in_use")

    category, relative_folder, rename_pattern = resolve_destination_folder(
        path, rules=rules, topics=topics
    )
    dest_dir = safe_destination_dir(relative_folder) if relative_folder else None
    if dest_dir is None:
        return {
            "filename": path.name,
            "current_path": str(path),
            "would_move_to": None,
            "category": category,
            "status": "review",
            "reason": "No hay una categoria fiable; se deja en su carpeta actual.",
            "relative_folder": relative_folder,
            "rename_pattern": rename_pattern,
        }

    topic_name = category.split(": ", 1)[1] if category.startswith("tema: ") else None
    filename = format_rename_pattern(rename_pattern, path, category, topic_name) if rename_pattern else path.name
    destination = dest_dir / filename
    status = "already_there" if destination.parent.resolve() == path.parent.resolve() else "move"
    return {
        "filename": path.name,
        "current_path": str(path),
        "would_move_to": str(destination),
        "category": category,
        "status": status,
        "cleanup_reason": cleanup_reason_for(destination),
        "relative_folder": relative_folder,
        "rename_pattern": rename_pattern,
    }


def _remove_empty_source_dirs(root: Path) -> None:
    """Remove only empty directories created by a download, never data."""
    if not root.exists() or not root.is_dir() or root.is_symlink():
        return
    try:
        for current, dirs, _files in os.walk(root, topdown=False):
            current_path = Path(current)
            if current_path == root or is_protected_path(current_path):
                continue
            try:
                current_path.rmdir()
            except OSError:
                pass
        if not any(root.iterdir()) and not is_protected_path(root):
            root.rmdir()
    except OSError:
        pass


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
    if path.name in RESERVED_DIR_NAMES:
        return True

    try:
        resolved = path.resolve()
        if resolved in (HOME_DIR.resolve(), DOWNLOADS_DIR.resolve()):
            return True
        if resolved in PROTECTED_PATHS:
            return True

        for d in get_cached_scan_dirs():
            if resolved == d:
                return True
    except (OSError, ValueError):
        pass

    return False


def organize_folder(
    path: Path,
    rules: list[dict] | None = None,
    topics: list[dict] | None = None,
) -> dict | None:
    """Organiza el contenido de una carpeta descargada archivo a archivo.

    Las carpetas descargadas suelen mezclar PDFs, imágenes, instaladores y
    subcarpetas. Moverlas como una sola unidad hacia ``Other`` solo cambia el
    sitio del desorden, así que ahora cada hijo obtiene su propio destino. Las
    carpetas vacías que quedan después se eliminan; las que aún contienen
    archivos desconocidos se conservan para que el usuario pueda revisarlas.
    """
    if not path.exists() or not path.is_dir():
        return None

    # Nunca seguir un enlace simbolico: moverlo arrastraria la carpeta real,
    # que puede estar en cualquier sitio del sistema.
    if path.is_symlink():
        return None

    if is_destination_or_reserved_dir(path) or is_protected_path(path):
        return None

    if is_file_in_use(path):
        return None

    files = _iter_folder_files(path)
    if not files:
        return None

    moved: list[dict] = []
    for child in files:
        if not child.exists() or is_file_in_use(child):
            continue
        result = organize_file(child, rules=rules, topics=topics)
        if result:
            moved.append(result)

    _remove_empty_source_dirs(path)
    if not moved:
        return None

    first = moved[0]
    first_destination = Path(first["destination"])
    return {
        "filename": path.name,
        "source": str(path),
        # Compatibilidad con callers que esperaban un movimiento de carpeta;
        # las operaciones reales quedan disponibles en ``items``.
        "destination": _portable_path(first_destination.parent),
        "category": first.get("category", "carpeta organizada"),
        "is_dir": True,
        "items": moved,
        "items_moved": len(moved),
        "items_review": max(0, len(files) - len(moved)),
    }


def organize_file(
    path: Path,
    rules: list[dict] | None = None,
    planned: dict | None = None,
    topics: list[dict] | None = None,
) -> dict | None:
    """Mueve un archivo o carpeta a su ubicación correspondiente. Devuelve info del
    movimiento, o None si no se movio (ya no existe, destino invalido,
    o ya esta en su carpeta de destino).

    'rules' evita releer las reglas de la base de datos en cada archivo cuando
    se organiza un directorio entero. 'planned' permite ejecutar exactamente
    la decision que ya tomo la simulacion o el informe del barrido.
    """
    if not path.exists():
        return None

    if path.is_dir():
        return organize_folder(path, rules=rules, topics=topics)

    # Un enlace simbolico se moveria a si mismo dejando el enlace roto, o
    # peor: apuntando fuera de la carpeta personal.
    if path.is_symlink():
        return None

    if not path.is_file():
        return None

    if is_temporary_download_file(path) or is_protected_path(path):
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

        with _move_lock:
            extract_dir = _unique_destination(path.parent, folder_name or f"{path.name}_extraido")
        try:
            unpack_archive(path, extract_dir)
            # El comprimido NO se borra: antes se hacia path.unlink() y luego
            # "Deshacer" solo renombraba la carpeta extraida a "algo.zip", asi
            # que el archivo original era irrecuperable. Ahora se archiva de
            # forma normal (movimiento reversible) y la extraccion se registra
            # como evento no reversible aparte.
            db.log_move(
                filename=path.name,
                source=str(path),
                destination=str(extract_dir),
                category="desempaquetado",
                undoable=False,
            )
            logger.info("desempaquetado %s en %s", path.name, extract_dir)
        except Exception as exc:
            logger.warning("no se pudo desempaquetar %s, continuando clasificacion normal: %s", path.name, exc)
            if extract_dir.exists() and extract_dir.is_dir():
                try:
                    shutil.rmtree(extract_dir)
                except OSError:
                    logger.debug("no se pudo limpiar %s tras un desempaquetado fallido", extract_dir)

    if planned is None:
        category, relative_folder, rename_pattern = resolve_destination_folder(
            path, rules=rules, topics=topics
        )
    else:
        category = planned.get("category", "review")
        relative_folder = planned.get("relative_folder")
        rename_pattern = planned.get("rename_pattern")

    # Unknown extensions intentionally remain in their source folder.  A
    # generic destination would only hide the item in an "Other" dump.
    if not relative_folder:
        logger.info("se deja para revision (%s): %s", category, path.name)
        return None

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
            # stat() puede fallar si otro worker mueve o borra el destino justo
            # entre el exists() y esta linea: se trata como "no es duplicado".
            try:
                is_identical = (
                    destination.is_file()
                    and destination.stat().st_size == path.stat().st_size
                    and calculate_sha256(destination) == calculate_sha256(path)
                )
            except OSError:
                is_identical = False

            if is_identical:
                action = db.get_setting("duplicate_action", "suffix")
                if action == "delete_source":
                    try:
                        # A la papelera, nunca unlink(): "el destino ya tiene
                        # una copia identica" es una comparacion por hash, pero
                        # un borrado equivocado aqui seria irrecuperable.
                        trash.move_to_trash(path)
                        logger.info("Duplicado enviado a la papelera: %s (ya existe identico en destino)", path.name)
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

    cleanup = _register_cleanup_candidate(destination, category)

    db.log_move(
        filename=path.name,
        source=source_str,
        destination=str(destination),
        category=category,
        undoable=not (cleanup and cleanup.get("action") == "deleted"),
    )
    result = {
        "filename": path.name,
        "source": _portable_path(Path(source_str)),
        "destination": _portable_path(destination),
        "category": category,
    }
    if cleanup:
        result["cleanup"] = cleanup
    return result


def organize_directory_report(directory: Path) -> dict:
    """Planifica y ejecuta un barrido completo, devolviendo todos sus estados.

    La simulacion y este barrido usan `_build_file_plan`. Asi, un archivo que
    la vista previa marca como revision no puede acabar escondido en otra
    carpeta durante la ejecucion real, y la interfaz puede explicar tambien
    los archivos temporales, vacios o bloqueados.
    """
    report = {"items": [], "review": [], "skipped": [], "truncated": False}
    if not directory.exists() or not directory.is_dir():
        return report

    rules = db.list_rules()
    topics = db.list_topics()
    candidates, source_dirs, truncated = _iter_directory_file_candidates(directory)
    report["truncated"] = truncated

    for path in candidates:
        plan = _build_file_plan(path, rules, topics=topics)
        status = plan.get("status")
        if status == "review":
            report["review"].append(plan)
            continue
        if status != "move":
            report["skipped"].append(plan)
            continue

        result = organize_file(path, rules=rules, planned=plan, topics=topics)
        if result:
            report["items"].append(result)
        else:
            report["skipped"].append({
                **plan,
                "status": "skipped",
                "reason": "No se pudo mover despues de preparar el plan.",
            })

    for source_dir in source_dirs:
        _remove_empty_source_dirs(source_dir)

    return report


def organize_directory(directory: Path) -> list[dict]:
    """Compatibilidad: ejecuta un barrido y devuelve solo los movimientos."""
    return organize_directory_report(directory)["items"]


def simulate_directory(directory: Path, max_files: int | None = None) -> list[dict]:
    """Build the complete non-mutating plan used by the preview dialog.

    The optional limit is explicit for callers that need a bounded probe. The
    normal API passes no limit, so the user receives every move, review and
    skipped item instead of a silent first-page slice.
    """
    if not directory.exists() or not directory.is_dir():
        return []

    rules = db.list_rules()
    topics = db.list_topics()
    candidates, _source_dirs, truncated = _iter_directory_file_candidates(
        directory, max_files=max_files
    )
    plan = [_build_file_plan(path, rules, topics=topics) for path in candidates]
    if truncated:
        plan.append({
            "filename": "Vista previa limitada",
            "current_path": str(directory),
            "would_move_to": None,
            "category": "preview",
            "status": "truncated",
            "reason": "La vista previa alcanzo el limite solicitado.",
        })
    return plan


def undo_move(move_id: int) -> tuple[dict | None, str | None]:
    """Devuelve un archivo del historial a su carpeta de origen.
    Retorna (datos_movimiento, mensaje_error)."""
    move = db.get_move(move_id)
    if not move:
        return None, "movimiento no encontrado en la base de datos"
    if move["undone_at"]:
        return None, "este movimiento ya fue deshecho anteriormente"

    # Un desempaquetado o un borrado de mantenimiento no son movimientos: no
    # hay nada que devolver a su sitio. Antes se intentaba igualmente, con
    # resultados absurdos (una carpeta renombrada a "algo.zip", o un
    # Path("DELETED") interpretado como ruta relativa al directorio de trabajo).
    if not move.get("undoable", 1):
        if move["category"] == "mantenimiento":
            return None, "los borrados de mantenimiento se recuperan desde la papelera, no desde el historial"
        return None, "esta accion no se puede deshacer desde el historial"

    dest_path = Path(move["destination"])
    orig_path = Path(move["source"])

    if not dest_path.exists():
        return None, f"el archivo ya no esta en su carpeta de destino ({dest_path.name})"

    # El origen se guardo como ruta absoluta cuando se hizo el movimiento; se
    # vuelve a validar por si la base de datos fue manipulada.
    if resolve_safe_path(str(orig_path)) is None:
        return None, "la carpeta de origen registrada esta fuera de tu carpeta personal"

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

        # Una regla sobre "~", "~/.config" o similar borraria la configuracion
        # entera del usuario. Se rechaza aunque este guardada en la BD.
        if is_protected_path(resolved_dir):
            logger.error(
                "Regla de mantenimiento sobre una ruta protegida (%s); se ignora", resolved_dir
            )
            continue

        # 3. Recorrer de forma recursiva
        for root, dirs, files in os.walk(resolved_dir):
            # No entrar en carpetas ocultas ni reservadas: ahi viven las
            # configuraciones de otras aplicaciones, no archivos caducables.
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in RESERVED_DIR_NAMES
                and not (Path(root) / d).is_symlink()
            ]

            for file in files:
                file_path = Path(root) / file
                if file.startswith("."):
                    continue  # dotfiles: configuracion, no basura caducable
                if file_path.is_symlink():
                    continue
                # Segunda validacion de seguridad para cada archivo recorrido (evitar escape por enlaces simbolicos o similares)
                resolved_file_path = resolve_safe_path(str(file_path))
                if not resolved_file_path or is_protected_path(resolved_file_path):
                    continue

                try:
                    stat_info = resolved_file_path.stat()
                    # Comprobar la edad
                    age_days = (current_time - stat_info.st_mtime) / 86400
                    if age_days <= max_age_days:
                        continue

                    # A la PAPELERA, no unlink(): una regla mal configurada no
                    # puede destruir documentos de forma irreversible.
                    outcome = trash.move_to_trash(resolved_file_path)
                    db.log_move(
                        filename=resolved_file_path.name,
                        source=str(resolved_file_path),
                        destination=f"papelera:{outcome['method']}",
                        category="mantenimiento",
                        undoable=False,
                    )
                    deleted_files.append({
                        "filename": resolved_file_path.name,
                        "path": str(resolved_file_path),
                        "age_days": round(age_days, 2),
                        "trash_method": outcome["method"],
                        "trash_id": outcome["entry_id"],
                    })
                    logger.info(
                        "Mantenimiento: %s enviado a la papelera (edad: %.2f dias)",
                        resolved_file_path, age_days,
                    )
                except OSError as exc:
                    logger.error("Error al procesar/eliminar %s en mantenimiento: %s", file_path, exc)

        _remove_empty_dirs(resolved_dir)

    # Purga lo que ya haya caducado en la papelera propia de Martix.
    try:
        trash.purge()
    except Exception:
        logger.debug("no se pudo purgar la papelera", exc_info=True)

    return deleted_files


def _remove_empty_dirs(root: Path) -> None:
    """Elimina las carpetas que quedaron vacias tras el barrido (nunca la raiz).

    Sin esto, el mantenimiento dejaba un esqueleto de carpetas vacias creciendo
    indefinidamente.
    """
    for current, dirs, files in os.walk(root, topdown=False):
        current_path = Path(current)
        if current_path == root or current_path.is_symlink():
            continue
        if is_protected_path(current_path):
            continue
        try:
            if not any(current_path.iterdir()):
                current_path.rmdir()
                logger.debug("carpeta vacia eliminada: %s", current_path)
        except OSError:
            continue

