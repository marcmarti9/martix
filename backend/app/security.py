"""Proteccion de la API y validacion de rutas de destino.

Martix maneja documentos sensibles (extractos bancarios, facturas...), asi
que aunque solo escuche en localhost hay dos ataques realistas que cerrar:

- CSRF / DNS rebinding: una web abierta en tu navegador puede lanzar POSTs
  "a ciegas" contra 127.0.0.1 o resolver su dominio a tu IP local. Se
  bloquea comprobando las cabeceras Host y Origin de cada peticion.
- Path traversal: una regla o Tema con destino "../../x" o una ruta
  absoluta moveria archivos fuera de tu carpeta personal. Se bloquea
  normalizando y validando cada destino antes de guardarlo y de usarlo.
"""

import hmac
import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit

from config.settings import API_TOKEN, HOME_DIR, HOST, PORT

# Nombres de host desde los que es legitimo hablar con Martix cuando
# escucha solo en local.
_LOCAL_HOSTNAMES = {"127.0.0.1", "localhost", "[::1]", "::1"}

_EXTENSION_RE = re.compile(r"^[a-z0-9]{1,16}$")

# "C:", "d:algo"... una ruta relativa a unidad de Windows nunca es un destino
# valido dentro de la carpeta personal.
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")

# Nombres de dispositivo reservados en Windows: crear una carpeta con estos
# nombres falla o se comporta de forma imprevisible.
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


# ---- validacion de destinos -------------------------------------------------

def clean_destination(raw: str) -> str | None:
    """Normaliza un destino escrito por el usuario a una ruta relativa
    segura dentro de su carpeta personal ("Documents/Banco"). Devuelve None
    si es invalido o intenta escaparse (absoluta, unidades de Windows, "..").
    """
    text = (raw or "").strip().replace("\\", "/")
    if not text:
        return None
    # rutas absolutas o con unidad de Windows ("C:...") no se admiten
    if PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute():
        return None
    if "\x00" in text:
        return None

    parts = [p.strip() for p in text.split("/")]
    parts = [p for p in parts if p and p != "."]
    if not parts or any(p == ".." for p in parts):
        return None

    for part in parts:
        # "C:algo" (ruta relativa a unidad) y flujos alternativos NTFS
        # ("archivo:stream") siguen prohibidos, pero un ":" suelto es un
        # nombre de carpeta legitimo en Linux/macOS ("Music/AC:DC").
        if _WINDOWS_DRIVE_RE.match(part):
            return None
        if ":" in part and os.name == "nt":
            return None
        if part.rstrip(". ") != part:
            # Windows ignora puntos/espacios finales: "Docs " y "Docs" serian
            # la misma carpeta, lo que permite colisiones inesperadas.
            return None
        if part.upper().split(".", 1)[0] in _WINDOWS_RESERVED_NAMES:
            return None
        if len(part) > 255:
            return None

    cleaned = "/".join(parts)
    if len(cleaned) > 1024:
        return None
    # comprobacion final contra la ruta real (cinturon y tirantes)
    resolved = (HOME_DIR / cleaned).resolve()
    home = HOME_DIR.resolve()
    if resolved != home and home not in resolved.parents:
        return None
    return cleaned


def safe_destination_dir(relative_folder: str) -> Path | None:
    """Convierte una carpeta relativa (ya guardada en la BD) en la ruta
    absoluta de destino, verificando otra vez que cae dentro de la carpeta
    personal. Ultima linea de defensa antes de mover nada."""
    cleaned = clean_destination(relative_folder)
    if cleaned is None:
        return None
    return HOME_DIR / cleaned


def valid_extension(raw: str) -> str | None:
    ext = (raw or "").strip().lower().lstrip(".")
    if ext == "*":
        return "*"
    return ext if _EXTENSION_RE.fullmatch(ext) else None


# Campos/operadores que organizer.check_conditions() sabe evaluar, y que el
# selector de reglas del frontend expone. Cualquier otro valor se rechaza
# antes de guardarlo: si no se valida aqui, un JSON de reglas importado (o
# una llamada directa a la API) podria colar cadenas arbitrarias que luego
# el frontend renderiza como texto de la condicion.
_VALID_CONDITION_FIELDS = {
    "name", "stem", "extension", "size_kb", "age_days", "content",
    "artist", "album", "title", "year", "camera", "exif_date",
}
# Debe coincidir exactamente con lo que organizer.check_conditions() evalua:
# "gte"/"lte" estaban implementados pero no permitidos aqui, asi que la API
# rechazaba con un 400 reglas que el motor sabia aplicar perfectamente.
_VALID_CONDITION_OPERATORS = {
    "contains", "not_contains", "equals", "starts_with", "ends_with",
    "gt", "lt", "gte", "lte",
}

# Campos numericos: su valor debe poder convertirse a numero o la regla no
# llegara a casar nunca (y el usuario no sabra por que).
_NUMERIC_CONDITION_FIELDS = {"size_kb", "age_days"}

MAX_CONDITIONS_PER_RULE = 20
MAX_CONDITION_VALUE_CHARS = 500


def valid_conditions(raw) -> str | None:
    """Valida y normaliza la lista de condiciones de una regla (ya sea un
    JSON string o una lista/objeto ya parseado). Devuelve el JSON normalizado
    o None si el formato o alguno de sus campos/operadores no es valido."""
    import json

    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if not isinstance(raw, list) or len(raw) > MAX_CONDITIONS_PER_RULE:
        return None

    cleaned = []
    for cond in raw:
        if not isinstance(cond, dict):
            return None
        field = cond.get("field")
        operator = cond.get("operator")
        value = cond.get("value")
        if field not in _VALID_CONDITION_FIELDS or operator not in _VALID_CONDITION_OPERATORS:
            return None
        # bool es subclase de int en Python: se descarta explicitamente para
        # que un true/false del JSON no acabe comparandose como 1/0.
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            return None
        if isinstance(value, str):
            if len(value) > MAX_CONDITION_VALUE_CHARS or "\x00" in value:
                return None
        if field in _NUMERIC_CONDITION_FIELDS:
            try:
                float(value)
            except (TypeError, ValueError):
                return None
        cleaned.append({"field": field, "operator": operator, "value": value})

    return json.dumps(cleaned) if cleaned else None


# ---- rutas que Martix nunca debe mover ni borrar ----------------------------

# Carpetas cuyo nombre indica que son de una herramienta o del sistema: moverlas
# rompe proyectos, entornos virtuales o el propio escritorio del usuario.
RESERVED_DIR_NAMES = frozenset({
    "node_modules", ".venv", "venv", "__pycache__", ".git", ".svn", ".hg",
    "scratch", "dist", "build", ".cache", ".local", ".config", ".ssh", ".gnupg",
    "AppData", "Library", "System", "Windows", "Program Files",
})

# Rutas que solo se protegen por COINCIDENCIA EXACTA: la carpeta personal y la
# raiz del sistema no se pueden mover ni borrar, pero por supuesto si su
# contenido (si no, Martix no podria organizar nada).
def _build_exact_protected() -> frozenset[Path]:
    home = HOME_DIR.resolve()
    return frozenset({home, Path(home.anchor), *home.parents})


# Subarboles intocables: ni ellos ni NADA de su interior. Contienen
# credenciales, claves o la configuracion del escritorio, y un error de
# configuracion (una regla de mantenimiento sobre "~") no puede llevarselos.
_PROTECTED_SUBTREE_RELATIVE = (
    ".ssh", ".gnupg", ".pki", ".password-store", ".aws", ".kube", ".docker",
    ".config", ".local", ".cache", ".mozilla", ".thunderbird",
    ".gitconfig", ".bashrc", ".zshrc", ".profile", ".bash_profile",
    "AppData", "Library", "Applications",
    ".martix", ".claude",
)

# Nombres de carpeta protegidos en cualquier nivel del arbol: aunque el usuario
# guarde un proyecto en ~/Documents, su .git o su .ssh siguen siendo intocables.
PROTECTED_DIR_NAMES = frozenset({
    ".ssh", ".gnupg", ".pki", ".password-store", ".aws", ".kube",
    ".git", ".svn", ".hg",
})


def _build_protected_subtrees() -> frozenset[Path]:
    home = HOME_DIR.resolve()
    paths = {home / rel for rel in _PROTECTED_SUBTREE_RELATIVE}
    try:
        from config.settings import DATA_DIR, DB_PATH
        paths.add(Path(DATA_DIR).resolve())
        paths.add(Path(DB_PATH).parent.resolve())
    except Exception:
        pass
    return frozenset(paths)


EXACT_PROTECTED_PATHS = _build_exact_protected()
PROTECTED_SUBTREES = _build_protected_subtrees()
# Compatibilidad con codigo que esperaba un unico conjunto.
PROTECTED_PATHS = EXACT_PROTECTED_PATHS | PROTECTED_SUBTREES


def is_protected_path(path: Path) -> bool:
    """True si la ruta es critica y Martix no debe moverla ni borrarla.

    Ultima barrera antes de cualquier borrado: el analizador de espacio y la
    limpieza de duplicados aceptan rutas que vienen de la interfaz, y una
    interfaz puede estar comprometida (o el usuario puede equivocarse de
    casilla).
    """
    try:
        resolved = Path(path).resolve()
    except (OSError, ValueError):
        return True  # si no se puede resolver, se trata como intocable

    # La carpeta personal y la raiz: solo ellas mismas, no su contenido.
    if resolved in EXACT_PROTECTED_PATHS:
        return True

    # Subarboles completos.
    for protected in PROTECTED_SUBTREES:
        if resolved == protected or protected in resolved.parents:
            return True

    return any(part in PROTECTED_DIR_NAMES for part in resolved.parts)


# ---- proteccion de las peticiones HTTP -------------------------------------

def _hostname_of(value: str) -> str:
    """Extrae el hostname (sin puerto) de una cabecera Host u Origin."""
    if not value:
        return ""
    if "//" not in value:
        value = "//" + value
    try:
        return (urlsplit(value).hostname or "").lower()
    except ValueError:
        return ""


def _is_trusted_hostname(hostname: str) -> bool:
    if hostname in _LOCAL_HOSTNAMES:
        return True
    # si el usuario expone Sortix en su LAN (HOST=0.0.0.0 o una IP concreta),
    # acepta tambien el nombre/IP con el que llega, ya que en ese modo el
    # acceso esta protegido por el token obligatorio.
    return HOST not in ("127.0.0.1", "localhost", "::1") and bool(hostname)


def check_request(request) -> tuple[dict, int] | None:
    """Devuelve None si la peticion es legitima, o (payload, status) para
    rechazarla. Se aplica a todas las rutas (API y frontend)."""

    # 1) anti DNS-rebinding: la cabecera Host debe ser la esperada.
    if not _is_trusted_hostname(_hostname_of(request.host)):
        return {"error": "peticion rechazada: cabecera Host no reconocida"}, 403

    # 2) anti CSRF: en metodos que cambian estado, si el navegador envia
    #    Origin, este debe ser tambien local/confiable.
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("Origin", "")
        if origin and origin != "null":
            if not _is_trusted_hostname(_hostname_of(origin)):
                return {"error": "peticion rechazada: origen no permitido"}, 403

    # 3) token compartido (obligatorio si Martix no escucha solo en local).
    if API_TOKEN and request.path.startswith("/api/"):
        supplied = request.headers.get("X-Martix-Token") or request.headers.get("X-Sortix-Token", "")
        if not hmac.compare_digest(supplied, API_TOKEN):
            return {"error": "token invalido o ausente"}, 401

    return None


def listening_beyond_localhost() -> bool:
    return HOST not in ("127.0.0.1", "localhost", "::1")


# ---- destinos de salida permitidos (anti-SSRF) ------------------------------

def is_loopback_url(url: str) -> bool:
    """True solo si la URL apunta a este mismo equipo por http/https.

    Martix hace exactamente UNA peticion saliente: al LLM local. Sin esta
    comprobacion, el endpoint que "prueba la conexion con Ollama" acepta
    cualquier URL y la solicita desde el servidor, convirtiendo a Martix en un
    proxy para sondear la red interna del usuario o servicios que solo escuchan
    en localhost (SSRF). Ademas es lo que respalda la promesa de privacidad:
    el contenido de los documentos no puede salir del equipo.
    """
    import ipaddress
    from urllib.parse import urlparse

    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    if hostname == "localhost":
        return True

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        # Un nombre de dominio podria resolver hoy a 127.0.0.1 y manana a otra
        # cosa (DNS rebinding), asi que solo se admiten IPs literales.
        return False

    return address.is_loopback


__all__ = [
    "API_TOKEN",
    "PORT",
    "PROTECTED_DIR_NAMES",
    "PROTECTED_PATHS",
    "PROTECTED_SUBTREES",
    "RESERVED_DIR_NAMES",
    "check_request",
    "clean_destination",
    "is_protected_path",
    "listening_beyond_localhost",
    "safe_destination_dir",
    "valid_conditions",
    "valid_extension",
]
