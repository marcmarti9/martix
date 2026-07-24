"""Decide en que categoria (y, si coincide con alguno de tus Temas
personalizados: banco, gimnasio, una app concreta, lo que sea) cae un
archivo. Mira primero el nombre del archivo y, si hace falta, el contenido
(PDF / DOCX / TXT) buscando las palabras clave de cada Tema."""

import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
import shutil
from pathlib import Path

from app import db, llm
from config.settings import load_categories

# Intentar importar dependencias de OCR (opcional)
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = shutil.which("tesseract") is not None
except ImportError:
    _OCR_AVAILABLE = False


MAX_CONTENT_CHARS = 20_000  # suficiente para detectar el tema sin leer el pdf entero
PDF_PAGES_TO_SCAN = 6
MIN_KEYWORD_HITS = 1

_categories = load_categories()

# extension -> nombre de categoria (p.ej. "pdf" -> "documents")
_EXT_TO_CATEGORY: dict[str, str] = {}
for _cat_name, _cat_data in _categories["categories"].items():
    for _ext in _cat_data["extensions"]:
        _EXT_TO_CATEGORY[_ext.lower()] = _cat_name

_CONTENT_EXTENSIONS = set(_categories["topic_matching"]["content_extensions"])
if _OCR_AVAILABLE:
    _CONTENT_EXTENSIONS.update({"png", "jpg", "jpeg", "tiff", "bmp", "gif"})


def normalize(text: str) -> str:
    """minusculas, sin tildes/diacriticos y con separadores (_, -, .) convertidos
    en espacios, para que "banco_extracto3" o "netflix-factura" tambien casen
    con la palabra clave suelta."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""
    chunks = []
    for page in reader.pages[:PDF_PAGES_TO_SCAN]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
        if sum(len(c) for c in chunks) >= MAX_CONTENT_CHARS:
            break
    return "".join(chunks)[:MAX_CONTENT_CHARS]


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W_TEXT_TAG = f"{{{_W_NS}}}t"

# Tope de bytes descomprimidos que se leen de un .docx (proteccion zip-bomb).
MAX_DOCX_BYTES = 8 * 1024 * 1024
_DOCX_CHUNK = 64 * 1024

# Defensa en profundidad frente a XXE / Billion Laughs. El parser de la
# biblioteca estandar no descarga entidades externas, y ademas rechazamos
# cualquier DTD por nuestra cuenta, pero si defusedxml esta instalado se usa
# porque prohibe DTDs y expansion de entidades a nivel de parser.
try:
    from defusedxml.ElementTree import iterparse as _DEFUSED_ITERPARSE
except Exception:  # pragma: no cover - depende del entorno
    _DEFUSED_ITERPARSE = None


class _LimitedReader:
    """Envuelve un stream para no leer jamas mas de `limit` bytes
    descomprimidos: un .docx de 30 KB no puede expandirse a gigabytes."""

    def __init__(self, stream, limit: int):
        self._stream = stream
        self._remaining = limit

    def read(self, size: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        if size is None or size < 0:
            size = self._remaining
        chunk = self._stream.read(min(size, self._remaining))
        self._remaining -= len(chunk)
        return chunk


def _extract_docx_text_defused(path: Path) -> str:
    """Variante con defusedxml: prohibe DTD y entidades a nivel de parser."""
    texts: list[str] = []
    total = 0
    try:
        with zipfile.ZipFile(path) as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            with zf.open("word/document.xml") as raw:
                stream = _LimitedReader(raw, MAX_DOCX_BYTES)
                for _event, elem in _DEFUSED_ITERPARSE(stream, events=("end",),
                                                       forbid_dtd=True,
                                                       forbid_entities=True,
                                                       forbid_external=True):
                    if elem.tag == _W_TEXT_TAG and elem.text:
                        texts.append(elem.text)
                        total += len(elem.text)
                    elem.clear()
                    if total >= MAX_CONTENT_CHARS:
                        break
    except Exception:
        return " ".join(texts)[:MAX_CONTENT_CHARS]
    return " ".join(texts)[:MAX_CONTENT_CHARS]


def _extract_docx_text(path: Path) -> str:
    """Extrae el texto de un .docx leyendo document.xml en streaming.

    Antes se hacia f.read(20_000) y luego ET.fromstring() sobre ese trozo:
    en cualquier documento real (>20 KB de XML, que son unas pocas paginas)
    el XML quedaba cortado a mitad, el parseo fallaba y se devolvia "". Es
    decir, la clasificacion por contenido de .docx no funcionaba nunca.

    Ahora se alimenta un parser incremental hasta juntar MAX_CONTENT_CHARS de
    texto, y si el documento estuviera danado se devuelve lo leido hasta ese
    punto en vez de nada.
    """
    if _DEFUSED_ITERPARSE is not None:
        return _extract_docx_text_defused(path)

    texts: list[str] = []
    total_chars = 0
    read_bytes = 0

    def _harvest(parser: ET.XMLPullParser) -> None:
        nonlocal total_chars
        for _event, elem in parser.read_events():
            if elem.tag == _W_TEXT_TAG and elem.text:
                texts.append(elem.text)
                total_chars += len(elem.text)
            # liberar memoria: los documentos largos generan miles de nodos
            elem.clear()

    try:
        with zipfile.ZipFile(path) as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            parser = ET.XMLPullParser(["end"])
            with zf.open("word/document.xml") as f:
                previous_tail = b""
                while total_chars < MAX_CONTENT_CHARS and read_bytes < MAX_DOCX_BYTES:
                    chunk = f.read(_DOCX_CHUNK)
                    if not chunk:
                        break
                    read_bytes += len(chunk)
                    # Prevencion de XXE / Billion Laughs: un .docx legitimo no
                    # lleva DTD. El solape evita que se cuele partiendo la
                    # cadena entre dos lecturas.
                    if b"<!DOCTYPE" in previous_tail + chunk or b"<!ENTITY" in previous_tail + chunk:
                        return ""
                    previous_tail = chunk[-16:]
                    parser.feed(chunk)
                    _harvest(parser)
    except Exception:
        # documento corrupto o truncado: devolvemos lo que se pudo leer
        return " ".join(texts)[:MAX_CONTENT_CHARS]

    return " ".join(texts)[:MAX_CONTENT_CHARS]


def _extract_txt_text(path: Path) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(MAX_CONTENT_CHARS)
    except Exception:
        return ""


_OCR_EXTENSIONS = ("png", "jpg", "jpeg", "tiff", "bmp", "gif")


def _extract_image_text(path: Path) -> str:
    if not _OCR_AVAILABLE:
        return ""
    try:
        # context manager: sin el, cada imagen analizada dejaba un descriptor
        # de archivo abierto hasta la siguiente pasada del recolector.
        with Image.open(path) as img:
            return pytesseract.image_to_string(img, timeout=10)[:MAX_CONTENT_CHARS]
    except Exception:
        return ""


def content_is_extractable(ext: str) -> bool:
    """Si Martix sabe leer el contenido de esta extension.

    Distinguir "no se pudo leer" de "se leyo y estaba vacio" es imprescindible
    para las condiciones: '' significaba que una condicion
    `content not_contains X` casaba con TODOS los binarios (mp4, xlsx, zip...)
    porque "" nunca contiene nada.
    """
    if ext in ("pdf", "docx", "txt"):
        return True
    return ext in _OCR_EXTENSIONS and _OCR_AVAILABLE


def _extract_content(path: Path, ext: str) -> str:
    if ext == "pdf":
        return _extract_pdf_text(path)
    if ext == "docx":
        return _extract_docx_text(path)
    if ext == "txt":
        return _extract_txt_text(path)
    if ext in _OCR_EXTENSIONS:
        return _extract_image_text(path)
    return ""


def _count_keyword_hits(text_normalized: str, keywords: list[str]) -> int:
    hits = 0
    for kw in keywords:
        kw_norm = normalize(kw)
        if not kw_norm:
            continue
        pattern = r"\b" + re.escape(kw_norm) + r"\b"
        hits += len(re.findall(pattern, text_normalized))
    return hits


def _best_topic_for_text(text: str, topics: list[dict]) -> dict | None:
    if not text.strip():
        return None
    text_norm = normalize(text)
    best_topic = None
    best_hits = 0
    for topic in topics:
        hits = _count_keyword_hits(text_norm, topic["keywords"])
        if hits > best_hits:
            best_hits = hits
            best_topic = topic
    return best_topic if best_hits >= MIN_KEYWORD_HITS else None


def detect_topic(path: Path, ext: str, topics: list[dict]) -> tuple[dict | None, str]:
    """Identifica a que Tema pertenece un documento: primero por el nombre del
    archivo (rapido) y, si no hay pista, por su contenido.

    Devuelve (tema, contenido_leido) para que quien llame pueda reutilizar el
    texto extraido (p. ej. el LLM) sin volver a abrir y parsear el archivo.
    """
    if not topics:
        return None, ""

    topic = _best_topic_for_text(path.stem, topics)
    if topic:
        return topic, ""

    if ext in _CONTENT_EXTENSIONS:
        content = _extract_content(path, ext)
        return _best_topic_for_text(content, topics), content

    return None, ""


def _match_subcategory(category: str, stem: str) -> dict | None:
    """Subcategorias descriptivas por patrones en el nombre del archivo
    (capturas de pantalla, facturas, curriculums...)."""
    stem_norm = normalize(stem)
    for sub in _categories["categories"][category].get("subcategories", []):
        for pattern in sub.get("patterns", []):
            pattern_norm = normalize(pattern)
            if pattern_norm and re.search(r"\b" + re.escape(pattern_norm) + r"\b", stem_norm):
                return sub
    return None


def classify_folder(path: Path) -> dict:
    """Clasifica un directorio entero según el nombre de la carpeta, temas,
    subcategorías o contenido predominante dentro del mismo."""
    stem = path.name

    # 1. Comprobar Temas del usuario por nombre de carpeta
    topics = db.list_topics()
    if topics:
        topic = _best_topic_for_text(stem, topics)
        if topic:
            return {
                "category": f"tema: {topic['name']}",
                "topic": topic["name"],
                "folder": topic["destination"],
                "rename_pattern": topic.get("rename_pattern")
            }

    # 2. Comprobar subcategorías por patrón en el nombre de la carpeta
    for cat_name in _categories["categories"]:
        sub = _match_subcategory(cat_name, stem)
        if sub:
            return {"category": sub["label"], "topic": None, "folder": sub["folder"]}

    # 3. Analizar extensión predominante dentro de la carpeta
    ext_counts: dict[str, int] = {}
    total_files = 0
    try:
        import os
        for root, _, files in os.walk(path):
            for f in files:
                if f.startswith("."):
                    continue
                ext = Path(f).suffix.lower().lstrip(".")
                if ext:
                    cat = _EXT_TO_CATEGORY.get(ext, "other")
                    ext_counts[cat] = ext_counts.get(cat, 0) + 1
                    total_files += 1
                if total_files >= 100:
                    break
            if total_files >= 100:
                break
    except OSError:
        pass

    if total_files > 0 and ext_counts:
        dominant_cat = max(ext_counts, key=ext_counts.get)
        dominant_count = ext_counts[dominant_cat]
        if dominant_count / total_files >= 0.4 and dominant_cat in _categories["categories"]:
            category_folder = _categories["categories"][dominant_cat]["folder"]
            return {"category": dominant_cat, "topic": None, "folder": category_folder}

    fallback_folder = _categories["categories"].get("other", {}).get("folder", "Other")
    return {"category": "other", "topic": None, "folder": fallback_folder}


def classify(path: Path) -> dict:
    """Devuelve {"category": str, "topic": str | None, "folder": str}
    donde 'folder' es la ruta relativa a la carpeta personal del usuario.

    Prioridad: Temas del usuario > subcategorias descriptivas por nombre >
    LLM local opcional (documentos) > carpeta base de la categoria."""
    if path.is_dir():
        return classify_folder(path)

    ext = path.suffix.lower().lstrip(".")
    category = _EXT_TO_CATEGORY.get(ext, "other")
    if category not in _categories["categories"]:
        category = "other"

    content = ""
    if ext in _CONTENT_EXTENSIONS:
        topic, content = detect_topic(path, ext, db.list_topics())
        if topic:
            return {
                "category": f"tema: {topic['name']}",
                "topic": topic["name"],
                "folder": topic["destination"],
                "rename_pattern": topic.get("rename_pattern"),
            }

    sub = _match_subcategory(category, path.stem)
    if sub:
        return {"category": sub["label"], "topic": None, "folder": sub["folder"]}

    category_folder = _categories["categories"][category]["folder"]

    if ext in _CONTENT_EXTENSIONS and llm.LLM_ENABLED:
        if not content:
            content = _extract_content(path, ext)
        suggested = llm.suggest_subfolder(path.name, content, category_folder)
        if suggested:
            return {"category": f"IA local: {suggested.rsplit('/', 1)[-1]}", "topic": None, "folder": suggested}

    return {"category": category, "topic": None, "folder": category_folder}


def extract_metadata(path: Path) -> dict[str, str | None]:
    """Extrae metadatos EXIF (imágenes) e ID3/audio (música) de forma segura.
    Retorna claves: artist, album, title, year, exif_date, camera.
    """
    res = {
        "artist": None,
        "album": None,
        "title": None,
        "year": None,
        "exif_date": None,
        "camera": None,
    }
    if not path or not path.exists() or not path.is_file():
        return res

    ext = path.suffix.lower().lstrip(".")

    # EXIF para .jpg, .jpeg, .png, .webp, .tiff
    if ext in ("jpg", "jpeg", "png", "webp", "tiff"):
        try:
            from PIL import Image, ExifTags
            with Image.open(path) as img:
                exif_data = img.getexif()
                make = None
                model = None
                date_val = None

                def process_exif_dict(exif_dict):
                    nonlocal make, model, date_val
                    for tag_id, value in exif_dict.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        if tag_name == "Make" and value and not make:
                            make = str(value).strip("\x00 ").strip()
                        elif tag_name == "Model" and value and not model:
                            model = str(value).strip("\x00 ").strip()
                        elif tag_name in ("DateTimeOriginal", "DateTime", "DateTimeDigitized") and value and not date_val:
                            date_val = str(value).strip("\x00 ").strip()

                if exif_data:
                    process_exif_dict(exif_data)

                if hasattr(img, "_getexif") and callable(img._getexif):
                    try:
                        raw_exif = img._getexif()
                        if raw_exif:
                            process_exif_dict(raw_exif)
                    except Exception:
                        pass

                if make or model:
                    if make and model:
                        if model.lower().startswith(make.lower()):
                            res["camera"] = model
                        else:
                            res["camera"] = f"{make} {model}"
                    else:
                        res["camera"] = make or model

                if date_val:
                    res["exif_date"] = date_val
        except Exception:
            pass

    # ID3 / Audio para .mp3, .flac, .m4a, .wav
    elif ext in ("mp3", "flac", "m4a", "wav"):
        try:
            import mutagen
            audio = None
            try:
                audio = mutagen.File(path, easy=True)
            except Exception:
                pass

            if audio is None:
                try:
                    audio = mutagen.File(path)
                except Exception:
                    pass

            def get_val_from_obj(obj, keys):
                for k in keys:
                    if hasattr(obj, "get") and callable(obj.get):
                        val = obj.get(k)
                        if val is not None:
                            if isinstance(val, (list, tuple)) and len(val) > 0:
                                s = str(val[0]).strip("\x00 ").strip()
                                if s:
                                    return s
                            else:
                                s = str(val).strip("\x00 ").strip()
                                if s:
                                    return s
                    if hasattr(obj, "__getitem__"):
                        try:
                            val = obj[k]
                            if isinstance(val, (list, tuple)) and len(val) > 0:
                                s = str(val[0]).strip("\x00 ").strip()
                                if s:
                                    return s
                            elif val is not None:
                                s = str(val).strip("\x00 ").strip()
                                if s:
                                    return s
                        except Exception:
                            pass
                return None

            if audio is not None:
                res["artist"] = get_val_from_obj(audio, ["artist", "TPE1", "\xa9ART", "ARTIST", "Artist"])
                res["album"] = get_val_from_obj(audio, ["album", "TALB", "\xa9alb", "ALBUM", "Album"])
                res["title"] = get_val_from_obj(audio, ["title", "TIT2", "\xa9nam", "TITLE", "Title"])
                year_raw = get_val_from_obj(audio, ["date", "year", "TYER", "TDRC", "\xa9day", "DATE", "Date"])
                if year_raw:
                    m = re.search(r"\b(19\d\d|20\d\d)\b", year_raw)
                    res["year"] = m.group(1) if m else year_raw

            if ext in ("mp3", "wav") and (not res["artist"] or not res["title"]):
                try:
                    from mutagen.id3 import ID3
                    id3 = ID3(path)
                    if not res["artist"] and "TPE1" in id3:
                        res["artist"] = str(id3["TPE1"]).strip("\x00 ").strip()
                    if not res["album"] and "TALB" in id3:
                        res["album"] = str(id3["TALB"]).strip("\x00 ").strip()
                    if not res["title"] and "TIT2" in id3:
                        res["title"] = str(id3["TIT2"]).strip("\x00 ").strip()
                    if not res["year"]:
                        y = str(id3["TDRC"]).strip("\x00 ").strip() if "TDRC" in id3 else (str(id3["TYER"]).strip("\x00 ").strip() if "TYER" in id3 else None)
                        if y:
                            m = re.search(r"\b(19\d\d|20\d\d)\b", y)
                            res["year"] = m.group(1) if m else y
                except Exception:
                    pass
        except Exception:
            pass

    return res
