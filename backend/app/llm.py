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

import json
import logging
import re
import urllib.request

from config.settings import LLM_ENABLED, LLM_MODEL, LLM_URL

logger = logging.getLogger("martix.llm")

MAX_EXCERPT_CHARS = 1200
TIMEOUT_SECONDS = 25

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


def _sanitize_folder_name(raw: str) -> str | None:
    text = (raw or "").strip().splitlines()[0] if (raw or "").strip() else ""
    text = text.strip("\"'` .")
    if "/" in text or "\\" in text or ".." in text or ":" in text:
        return None
    return text if _NAME_RE.fullmatch(text) else None


def suggest_subfolder(filename: str, content_excerpt: str, category_folder: str) -> str | None:
    """Devuelve una carpeta relativa "categoria/Nombre sugerido" o None si el
    LLM esta desactivado, no responde o la respuesta no es un nombre valido."""
    if not LLM_ENABLED:
        return None

    # Barrera de privacidad. Aqui viaja un fragmento del CONTENIDO del
    # documento (puede ser un extracto bancario o un contrato). LLM_URL sale
    # de .env, asi que un fichero mal copiado de un tutorial bastaria para
    # exfiltrarlo a un tercero en silencio: se comprueba en cada llamada que
    # el destino sigue siendo este mismo equipo.
    from app.security import is_loopback_url
    if not is_loopback_url(LLM_URL):
        logger.error(
            "MARTIX_LLM_URL apunta fuera de este equipo (%s). Martix no enviara el contenido "
            "de tus documentos a un servidor remoto; corrige backend/.env o desactiva MARTIX_LLM.",
            LLM_URL,
        )
        return None

    prompt = _PROMPT.format(
        filename=filename,
        excerpt=(content_excerpt or "")[:MAX_EXCERPT_CHARS],
    )
    payload = json.dumps({
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 12},
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            LLM_URL.rstrip("/") + "/api/generate",
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
