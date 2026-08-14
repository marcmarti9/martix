"""Carga la configuracion de Martix: variables de entorno (.env), rutas base
y el fichero de categorias. Sin dependencias externas para que corra en
cualquier maquina modesta."""

import json
import os
import sys
from pathlib import Path


FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    # PyInstaller extracts resources to a temporary directory.  It is valid for
    # read-only assets, but it is deleted when the application exits, so user
    # data must never be stored there.
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    PROJECT_DIR = RESOURCE_DIR
    BACKEND_DIR = RESOURCE_DIR / "backend" if (RESOURCE_DIR / "backend").exists() else RESOURCE_DIR
    CONFIG_DIR = RESOURCE_DIR / "config" if (RESOURCE_DIR / "config").exists() else RESOURCE_DIR
else:
    BACKEND_DIR = Path(__file__).resolve().parent.parent
    PROJECT_DIR = BACKEND_DIR.parent
    RESOURCE_DIR = PROJECT_DIR
    CONFIG_DIR = Path(__file__).resolve().parent

HOME_DIR = Path.home()


def _default_data_dir() -> Path:
    """Carpeta persistente de Martix segun la plataforma.

    En un ejecutable congelado no se puede usar ``_MEIPASS``: PyInstaller lo
    limpia al cerrar y eso haria desaparecer la base de datos, la papelera y
    las preferencias del usuario.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or (HOME_DIR / "AppData" / "Local")
        return Path(base) / "Martix"
    if sys.platform == "darwin":
        return HOME_DIR / "Library" / "Application Support" / "Martix"
    base = os.environ.get("XDG_DATA_HOME") or (HOME_DIR / ".local" / "share")
    return Path(base) / "martix"


def _load_env(env_path: Path) -> dict:
    """Parser minimo de .env (KEY=VALUE), sin depender de python-dotenv."""
    values = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


# Process environment is useful for the packaged application, while the
# project/data .env files keep the source workflow convenient.  A file value
# deliberately wins over the process value, matching the previous behavior.
_env = dict(os.environ)
_env.update(_load_env(BACKEND_DIR / ".env"))
_env.update(_load_env(_default_data_dir() / ".env"))

HOST = _env.get("HOST", "127.0.0.1")


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(_env.get(name, str(default))))
    except (TypeError, ValueError):
        return default


PORT = _env_int("PORT", 5000, minimum=0)

_downloads_override = _env.get("DOWNLOADS_DIR", "").strip()
DOWNLOADS_DIR = Path(_downloads_override).expanduser() if _downloads_override else Path.home() / "Downloads"


DATA_DIR = (
    Path(_env.get("MARTIX_DATA_DIR", "").strip()).expanduser()
    if _env.get("MARTIX_DATA_DIR", "").strip()
    else _default_data_dir()
)
TRASH_DIR = DATA_DIR / "trash"

# Source installs keep the historical database location for compatibility.
# Frozen builds persist under the OS application-data directory instead of the
# temporary PyInstaller extraction directory.
DB_PATH = (DATA_DIR / "martix.db") if FROZEN else (PROJECT_DIR / "database" / "martix.db")
_OLD_DB_PATH = PROJECT_DIR / "database" / "sortix.db"
if not FROZEN and not DB_PATH.exists() and _OLD_DB_PATH.exists():
    try:
        _OLD_DB_PATH.rename(DB_PATH)
    except Exception:
        pass

SCHEMA_PATH = RESOURCE_DIR / "database" / "scripts" / "schema.sql"
CATEGORIES_FILE = CONFIG_DIR / "categories.json"

# Dias que se conservan los archivos en la papelera de Martix antes de
# purgarse definitivamente.
TRASH_RETENTION_DAYS = _env_int("MARTIX_TRASH_RETENTION_DAYS", 30, minimum=1)

# Token compartido para la API (cabecera X-Martix-Token). Opcional mientras
# Martix escuche solo en 127.0.0.1; obligatorio si se expone HOST a la red.
API_TOKEN = _env.get("MARTIX_TOKEN", _env.get("SORTIX_TOKEN", "")).strip()


def _env_flag(name: str) -> bool:
    return _env.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


# LLM local (Ollama) para nombrar carpetas de documentos que no encajan en
# ningun Tema ni subcategoria. Apagado por defecto: solo se activa unica y
# exclusivamente si el usuario lo indica explicitamente (MARTIX_LLM=1).
LLM_ENABLED = _env_flag("MARTIX_LLM") or _env_flag("SORTIX_LLM")
LLM_AUTO = _env_flag("MARTIX_LLM_AUTO")
LLM_URL = _env.get("MARTIX_LLM_URL", _env.get("SORTIX_LLM_URL", "http://127.0.0.1:11434"))
LLM_MODEL = _env.get("MARTIX_LLM_MODEL", _env.get("SORTIX_LLM_MODEL", "llama3.2"))

import time

# Extensiones y prefijos de archivos temporales/parciales de navegadores
IGNORED_SUFFIXES = {
    ".crdownload",
    ".part",
    ".tmp",
    ".temp",
    ".download",
    ".partial",
    ".opdownload",
    ".fdown",
    ".utether",
    ".filepart",
}

IGNORED_PREFIXES = (
    "unconfirmed",
    "drive-download-",
    ".com.google.chrome",
    ".org.chromium",
    "~$",
    ".~",
)


def is_temporary_download_file(path: Path) -> bool:
    """Comprueba si un archivo es un artefacto temporal o parcial de descarga
    del navegador.

    Solo se mira el SUFIJO real y los prefijos conocidos. Buscar ".part" como
    subcadena en cualquier posicion marcaba como temporales archivos
    perfectamente normales ("pelicula.part1.rar", "datos.partition.csv",
    "informe.particular.pdf"), que quedaban sin archivar para siempre.
    """
    name_lower = path.name.lower()

    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True

    return any(name_lower.startswith(pref) for pref in IGNORED_PREFIXES)


def is_file_in_use(path: Path) -> bool:
    """Comprueba si un archivo está siendo escrito o mantenido abierto por otra
    aplicación (p.ej. el navegador).

    Importante: un archivo de SOLO LECTURA (modo 0444, adjunto, medio montado)
    no esta "en uso". Antes se abria siempre en "r+b", asi que el
    PermissionError por falta de permiso de escritura se confundia con un
    bloqueo y esos archivos no se archivaban nunca.
    """
    if not path.exists() or not path.is_file():
        return False

    if sys.platform == "win32":
        # En Windows el propio open() falla si otro proceso tiene el archivo
        # abierto en exclusiva. Para archivos de solo lectura se prueba en
        # modo lectura, que sigue detectando el bloqueo exclusivo.
        mode = "r+b" if os.access(path, os.W_OK) else "rb"
        try:
            with open(path, mode):
                return False
        except OSError:
            return True

    try:
        import fcntl
    except ImportError:  # plataforma sin flock: no se puede saber
        return False

    try:
        # flock() no exige permiso de escritura, asi que "rb" basta y ademas
        # funciona con archivos de solo lectura.
        with open(path, "rb") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                return True
    except PermissionError:
        # Ni siquiera se puede leer: no es cosa de un bloqueo, y bloquear el
        # archivado aqui solo dejaria el archivo dando vueltas en la cola.
        return False
    except OSError:
        return True

    return False


def load_categories() -> dict:
    with open(CATEGORIES_FILE, encoding="utf-8") as f:
        return json.load(f)
