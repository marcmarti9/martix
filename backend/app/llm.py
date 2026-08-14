"""Nombrado opcional de carpetas con un LLM 100% local (Ollama).

Apagado por defecto: solo se activa con MARTIX_LLM=1 en .env, pensado para
equipos con recursos de sobra. Cuando un documento no encaja en ningun Tema
ni subcategoria, se le pide a un modelo local (via http://127.0.0.1:11434)
un nombre corto de carpeta y el archivo se guarda en
"<carpeta de la categoria>/<ese nombre>".

Privacidad: el fragmento de texto del documento solo viaja a tu propio
Ollama en localhost, nunca a internet. Y ante cualquier fallo (Ollama
apagado, timeout, respuesta rara) se vuelve en silencio a la clasificacion
normal, asi que un PC modesto sin Ollama no nota nada.
"""

import ctypes
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from config import settings as _settings

logger = logging.getLogger("martix.llm")

MAX_EXCERPT_CHARS = 1200
TIMEOUT_SECONDS = 8
DISCOVERY_TIMEOUT_SECONDS = 1.5
MIN_RAM_BYTES = 8 * 1024 * 1024 * 1024
MIN_CPU_CORES = 4
MAX_AUTO_CALLS = 64

# These names remain module globals for compatibility with older integrations,
# but their values are updated after the local Ollama probe. Nothing is ever
# sent outside loopback.
LLM_URL = _settings.LLM_URL
LLM_MODEL = _settings.LLM_MODEL
LLM_ENABLED = False
LLM_AUTO = bool(getattr(_settings, "LLM_AUTO", False))

_state_lock = threading.Lock()
_initialize_lock = threading.Lock()
_state = {
    "initialized": False,
    "enabled": False,
    "available": False,
    "automatic": LLM_AUTO,
    "hardware_ok": False,
    "reason": "Pendiente de comprobar Ollama local.",
    "url": LLM_URL,
    "model": LLM_MODEL,
    "models": [],
}
_calls_used = 0

# nombre de carpeta valido: 2-32 caracteres, letras/numeros/espacios/guiones.
_NAME_RE = re.compile(r"^[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ][0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-]{1,31}$")

_PROMPT = (
    "Eres un archivador de documentos. Te doy el nombre de un archivo y un "
    "fragmento de su contenido. Responde SOLO con un nombre de carpeta corto "
    "y descriptivo en espanol (1 a 3 palabras, sin barras, sin comillas, sin "
    "punto final) donde guardarias este documento. Ejemplos de respuesta: "
    "Recetas, Apuntes de fisica, Seguro del coche.\n\n"
    "Archivo: {filename}\n"
    "Contenido:\n{excerpt}\n\n"
    "Carpeta:"
)


def _available_memory_bytes() -> int:
    """Return physical RAM without adding a dependency to the desktop build."""
    if os.name == "nt":
        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except Exception:
            return 0
        return 0

    try:
        with open("/proc/meminfo", encoding="ascii") as stream:
            for line in stream:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _hardware_status() -> tuple[bool, str]:
    ram = _available_memory_bytes()
    cores = os.cpu_count() or 1
    if ram and ram < MIN_RAM_BYTES:
        return False, "El equipo tiene menos de 8 GB de RAM; se mantiene el modo heurístico."
    if cores < MIN_CPU_CORES:
        return False, "El equipo tiene menos de 4 núcleos; se mantiene el modo heurístico."
    return True, "Recursos locales suficientes."


def _discover_models(url: str) -> list[str]:
    request = urllib.request.Request(
        url.rstrip("/") + "/api/tags",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=DISCOVERY_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [
        str(item.get("name", "")).strip()
        for item in payload.get("models", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]


def _ollama_executable() -> str | None:
    candidates = [shutil.which("ollama")]
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "")
        candidates.extend([
            os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe"),
            os.path.join(program_files, "Ollama", "ollama.exe"),
        ])
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def _start_local_ollama() -> bool:
    """Start an already-installed Ollama server, never install software."""
    executable = _ollama_executable()
    if not executable:
        return False
    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen(
            [executable, "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return True
    except OSError as exc:
        logger.info("no se pudo iniciar Ollama local: %s", exc)
        return False


def _choose_model(models: list[str], requested: str) -> str | None:
    if not models:
        return None
    requested = (requested or "").strip()
    if requested:
        for model in models:
            if model == requested or model.startswith(requested + ":"):
                return model
        return None

    preferred = ("llama3.2", "qwen2.5", "qwen3", "gemma3", "phi3", "mistral")
    for prefix in preferred:
        for model in models:
            if model == prefix or model.startswith(prefix + ":"):
                return model
    return models[0]


def _update_state(base_dict: dict | None = None, **changes) -> dict:
    global LLM_ENABLED, LLM_MODEL
    with _state_lock:
        if base_dict:
            _state.update(base_dict)
        _state.update(changes)
        LLM_ENABLED = bool(_state["enabled"])
        LLM_MODEL = str(_state["model"] or _settings.LLM_MODEL)
        return dict(_state)


def initialize(force: bool = False) -> dict:
    """Detect local Ollama once, strictly respecting user opt-in."""
    global LLM_URL, LLM_AUTO
    with _initialize_lock:
        with _state_lock:
            if _state["initialized"] and not force:
                return dict(_state)

        LLM_URL = str(_settings.LLM_URL).strip()
        LLM_AUTO = bool(getattr(_settings, "LLM_AUTO", False))
        explicit = bool(_settings.LLM_ENABLED)
        hardware_ok, hardware_reason = _hardware_status()
        base = {
            "initialized": True,
            "enabled": False,
            "available": False,
            "automatic": LLM_AUTO and not explicit,
            "hardware_ok": hardware_ok,
            "url": LLM_URL,
            "model": str(_settings.LLM_MODEL),
            "models": [],
        }

        if not explicit and not LLM_AUTO:
            return _update_state(base, reason="LLM local desactivado. Solo se activa si el usuario lo indica (MARTIX_LLM=1).")

        from app.security import is_loopback_url
        if not is_loopback_url(LLM_URL):
            return _update_state(
                base,
                reason="La dirección de Ollama no es local; Martix no enviará archivos fuera del equipo.",
            )

        if LLM_AUTO and not explicit and not hardware_ok:
            return _update_state(base, reason=hardware_reason)

        probe_error = None
        try:
            models = _discover_models(LLM_URL)
        except Exception as exc:
            probe_error = str(exc)
            models = []
            if explicit and hardware_ok and _start_local_ollama():
                for _ in range(6):
                    time.sleep(0.5)
                    try:
                        models = _discover_models(LLM_URL)
                        break
                    except Exception as retry_exc:
                        probe_error = str(retry_exc)

            if not models:
                return _update_state(
                    base,
                    reason=(
                        "Ollama local no está disponible; se usa el modo heurístico."
                        if not _ollama_executable()
                        else "Ollama está instalado pero no responde o no tiene un modelo local disponible."
                    ),
                    probe_error=probe_error,
                )

        selected = _choose_model(models, str(_settings.LLM_MODEL))
        if not selected:
            return _update_state(
                base,
                available=True,
                models=models,
                reason=(
                    f"El modelo solicitado '{_settings.LLM_MODEL}' no está instalado en Ollama local."
                    if _settings.LLM_MODEL
                    else "Ollama responde, pero no tiene ningún modelo local descargado."
                ),
            )

        return _update_state(
            base,
            enabled=True,
            available=True,
            model=selected,
            models=models,
            reason=("Ollama local activado manualmente por el usuario." if explicit
                    else "Ollama local activado automáticamente."),
        )


def status() -> dict:
    return initialize()


def is_enabled() -> bool:
    return bool(initialize().get("enabled"))


def _reserve_call() -> bool:
    """Bound automatic inference so a large Downloads folder stays usable."""
    global _calls_used
    if not is_enabled():
        return False
    with _state_lock:
        if _calls_used >= MAX_AUTO_CALLS:
            return False
        _calls_used += 1
        return True


def _sanitize_folder_name(raw: str) -> str | None:
    text = (raw or "").strip().splitlines()[0] if (raw or "").strip() else ""
    text = text.strip("\"'` .")
    if "/" in text or "\\" in text or ".." in text or ":" in text:
        return None
    return text if _NAME_RE.fullmatch(text) else None


def suggest_subfolder(filename: str, content_excerpt: str, category_folder: str) -> str | None:
    """Devuelve una carpeta relativa "categoria/Nombre sugerido" o None si el
    LLM esta desactivado, no responde o la respuesta no es un nombre valido."""
    if not _reserve_call():
        return None

    with _state_lock:
        runtime_url = str(_state["url"])
        runtime_model = str(_state["model"])

    # Barrera de privacidad. Aqui viaja un fragmento del CONTENIDO del
    # documento (puede ser un extracto bancario o un contrato). LLM_URL sale
    # de .env, asi que un fichero mal copiado de un tutorial bastaria para
    # exfiltrarlo a un tercero en silencio: se comprueba en cada llamada que
    # el destino sigue siendo este mismo equipo.
    from app.security import is_loopback_url
    if not is_loopback_url(runtime_url):
        logger.error(
            "MARTIX_LLM_URL apunta fuera de este equipo (%s). Martix no enviara el contenido "
            "de tus documentos a un servidor remoto; corrige backend/.env o desactiva MARTIX_LLM.",
            runtime_url,
        )
        return None

    prompt = _PROMPT.format(
        filename=filename,
        excerpt=(content_excerpt or "")[:MAX_EXCERPT_CHARS],
    )
    payload = json.dumps({
        "model": runtime_model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30s",
        "options": {"temperature": 0, "num_predict": 12},
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            runtime_url.rstrip("/") + "/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("LLM local no disponible (%s); clasificacion normal", exc)
        return None

    name = _sanitize_folder_name(data.get("response", ""))
    if name is None:
        logger.info("respuesta del LLM descartada por no ser un nombre valido")
        return None
    return f"{category_folder}/{name}"


def suggest_rule_from_correction(filename: str, to_folder: str, from_folder: str | None = None) -> dict:
    """Genera una regla sugerida basada en un movimiento corregido."""
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    ext_clean = ext.lstrip(".") if ext else "*"
    ext_dot = f".{ext_clean}" if ext_clean != "*" else "*"

    dest = (to_folder or "").replace("\\", "/").rstrip("/")
    if dest.endswith("/" + filename) or dest == filename:
        parent_str = str(Path(dest).parent).replace("\\", "/")
        dest = parent_str if parent_str != "." else dest

    try:
        from config.settings import HOME_DIR
        dest_p = Path(dest)
        if dest_p.is_absolute():
            dest = str(dest_p.resolve().relative_to(HOME_DIR.resolve())).replace("\\", "/")
    except Exception:
        pass

    rule_name = f"Move {ext_dot} to {dest}" if ext_clean != "*" else f"Move {filename} to {dest}"

    rule = {
        "name": rule_name,
        "extension": ext_clean,
        "destination": dest,
        "action": "move",
        "conditions": [
            {
                "field": "extension" if ext_clean != "*" else "name",
                "operator": "equals",
                "value": ext_dot if ext_clean != "*" else filename
            }
        ]
    }
    return rule
