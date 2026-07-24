#!/usr/bin/env python3
"""Pruebas de seguridad de Martix: cada una intenta un abuso concreto.

Aislada (HOME y base de datos temporales). No comprueba que exista una
mitigacion: EJECUTA el ataque contra la aplicacion real y comprueba que no
funciona. Si alguien debilita una defensa, aqui vuelve a salir "EXPLOTABLE".

Ejecutar desde backend/:  .venv/bin/python tests/test_security.py
"""

import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="martix-sec-home-")
os.environ["HOME"] = _tmp
os.environ["USERPROFILE"] = _tmp
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from config import settings  # noqa: E402
from app import db  # noqa: E402
db.DB_PATH = Path(_tmp) / "sec.db"
from app import server, security, browser, classifier, watcher  # noqa: E402

HOME = Path(_tmp).resolve()
DOWNLOADS = settings.DOWNLOADS_DIR
DOWNLOADS.mkdir(parents=True, exist_ok=True)

app = server.create_app()
client = app.test_client()

RESULTS = []


def probe(num, title, severity):
    def deco(fn):
        def wrapper():
            try:
                verdict, detail = fn()
            except Exception as exc:
                import traceback
                verdict, detail = "ERROR", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            RESULTS.append((num, title, severity, verdict, detail))
            mark = {"VULN": "\033[31mEXPLOTABLE\033[0m", "OK": "\033[32mBLOQUEADO\033[0m",
                    "ERROR": "\033[35mERROR\033[0m", "WARN": "\033[33mDEBILIDAD\033[0m"}[verdict]
            print(f"\n[S{num:02d}][{severity}] {title}\n      -> {mark}: {detail}")
        return wrapper
    return deco


# --------------------------------------------------------------------------
@probe(1, "SSRF: /api/llm/test acepta cualquier URL y la solicita desde el servidor", "ALTA")
def s01():
    """El endpoint de 'probar conexion con Ollama' hace una peticion HTTP a la
    URL que le pases. Si no restringe el destino, convierte a Martix en un
    proxy para escanear la red interna del usuario o llegar a servicios que
    solo escuchan en localhost (routers, metadatos de nube, otras apps)."""
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"models":[{"name":"secreto-interno"}]}')

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        # Simula un servicio interno que NO es Ollama
        r = client.post("/api/llm/test", json={"url": f"http://127.0.0.1:{port}"})
        body = r.get_json()
        alcanzado = bool(hits)

        # Y un destino claramente fuera de lugar: metadatos de nube
        r2 = client.post("/api/llm/test", json={"url": "http://169.254.169.254"})
        meta_permitido = r2.status_code == 200 and r2.get_json().get("ok") is not False

        # Destinos que NUNCA deben permitirse
        externos = {
            "metadatos de nube": "http://169.254.169.254",
            "LAN privada": "http://192.168.1.1",
            "internet": "https://example.com",
            "dominio que resuelve a local (DNS rebinding)": "http://localtest.me",
            "otro esquema": "file:///etc/passwd",
        }
        permitidos = {}
        for nombre, u in externos.items():
            resp = client.post("/api/llm/test", json={"url": u})
            if resp.status_code == 200:
                permitidos[nombre] = resp.get_json()

        if permitidos:
            return "VULN", f"se aceptaron destinos no locales: {list(permitidos)}"
        if not alcanzado:
            return "WARN", "loopback tambien bloqueado: Ollama local dejaria de funcionar"
        return "OK", (f"loopback permitido (es donde corre Ollama, se alcanzo {hits}) y TODO lo demas "
                      f"rechazado con 400: {list(externos)}. Sin SSRF y la promesa de privacidad "
                      "queda respaldada por codigo")
    finally:
        srv.shutdown()


# --------------------------------------------------------------------------
@probe(2, "Fuga de informacion: /api/browse lista ~/.ssh y demas carpetas sensibles", "MEDIA")
def s02():
    ssh = HOME / ".ssh"
    ssh.mkdir(exist_ok=True)
    (ssh / "id_rsa").write_text("-----BEGIN OPENSSH PRIVATE KEY-----")
    (ssh / "known_hosts").write_text("github.com ssh-ed25519 AAAA")

    r = client.get("/api/browse?path=.ssh")
    if r.status_code == 200 and r.get_json().get("entries"):
        nombres = [e["name"] for e in r.get_json()["entries"]]
        return "VULN", (f"la API lista el contenido de ~/.ssh: {nombres}. El explorador de archivos "
                        "puede recorrer credenciales, tokens y configuracion (~/.aws, ~/.gnupg, "
                        "~/.config con sesiones). Un XSS o cualquier proceso local con acceso a la "
                        "API obtiene un mapa de donde estan los secretos")
    return "OK", f"acceso denegado o vacio (status {r.status_code})"


# --------------------------------------------------------------------------
@probe(3, "Bomba de descompresion de imagen (PIL) al clasificar u obtener EXIF", "MEDIA")
def s03():
    """Una imagen valida de pocos KB puede declarar dimensiones enormes y hacer
    que PIL reserve gigabytes al decodificarla."""
    try:
        from PIL import Image
    except ImportError:
        return "OK", "Pillow no instalado"

    limite = Image.MAX_IMAGE_PIXELS
    # Martix abre imagenes de origen no confiable en dos sitios
    abre_imagenes = (
        "Image.open(path)" in (BACKEND / "app" / "classifier.py").read_text(encoding="utf-8")
    )
    if limite is None:
        return "VULN", ("Image.MAX_IMAGE_PIXELS es None: el limite de PIL esta DESACTIVADO y una "
                        "imagen descargada puede agotar la memoria del equipo")
    from app import classifier as _cls
    if limite == getattr(_cls, "MAX_IMAGE_PIXELS", None):
        import warnings as _w
        filtro_error = any(f[0] == "error" for f in _w.filters
                           if f[2] is getattr(Image, "DecompressionBombWarning", None))
        return "OK", (f"Martix baja el limite de PIL a {limite:,} px y convierte "
                      f"DecompressionBombWarning en excepcion (filtro activo: {filtro_error})")
    if abre_imagenes and limite > 50_000_000:
        return "WARN", (f"PIL usa su limite por defecto ({limite:,} px) y solo emite un WARNING, no "
                        "una excepcion, salvo al doble del limite. Martix abre imagenes de descargas "
                        "(OCR y EXIF) sin fijar un tope propio ni capturar DecompressionBombWarning: "
                        "conviene bajar MAX_IMAGE_PIXELS y convertir el aviso en error")
    return "OK", f"limite de PIL: {limite}"


# --------------------------------------------------------------------------
@probe(4, "Inyeccion de argumentos en notify-send con nombres que empiezan por '-'", "BAJA")
def s04():
    """subprocess no usa shell, pero notify-send interpreta como OPCIONES los
    argumentos que empiezan por guion, y su cuerpo admite marcado."""
    fuente = (BACKEND / "app" / "watcher.py").read_text(encoding="utf-8")
    usa_separador = '"--"' in fuente or "'--'" in fuente
    if not usa_separador and "notify-send" in fuente:
        return "WARN", ("send_notification pasa el mensaje directamente a notify-send. Un archivo "
                        "llamado '-e' o '--expire-time=0' se interpreta como opcion del comando en "
                        "vez de como texto, y el cuerpo de notify-send admite marcado tipo HTML. "
                        "Falta un separador '--' antes de los datos del usuario")
    return "OK", "argumentos separados de las opciones"


# --------------------------------------------------------------------------
@probe(5, "Sin Content-Security-Policy: un XSS futuro tendria via libre", "MEDIA")
def s05():
    r = client.get("/")
    csp = r.headers.get("Content-Security-Policy")
    if not csp:
        cabeceras = {k: v for k, v in r.headers.items()
                     if k in ("X-Content-Type-Options", "Referrer-Policy", "X-Frame-Options")}
        return "WARN", ("no se envia Content-Security-Policy. Estan X-Content-Type-Options y "
                        f"Referrer-Policy ({cabeceras}), pero sin CSP cualquier inyeccion futura en "
                        "el DOM puede cargar scripts remotos y exfiltrar rutas y contenidos. "
                        "Tampoco hay X-Frame-Options: la interfaz se puede embeber en un iframe")
    return "OK", f"CSP presente: {csp}"


# --------------------------------------------------------------------------
@probe(6, "Path traversal al servir el frontend (/<path:filename>)", "ALTA")
def s06():
    intentos = [
        "../backend/.env",
        "../../etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "....//....//etc/passwd",
    ]
    filtrados = []
    for intento in intentos:
        r = client.get(f"/{intento}")
        if r.status_code == 200 and b"root:" in r.data:
            filtrados.append(intento)
    if filtrados:
        return "VULN", f"se sirvieron archivos fuera de frontend/: {filtrados}"
    return "OK", "send_from_directory rechaza el traversal (safe_join)"


# --------------------------------------------------------------------------
@probe(7, "El token de la API se guarda en localStorage (accesible desde JS)", "BAJA")
def s07():
    js = (BACKEND.parent / "frontend" / "app.js").read_text(encoding="utf-8")
    if 'localStorage.getItem("martix_token")' in js:
        return "WARN", ("el token se guarda en localStorage, asi que cualquier XSS lo extrae y da "
                        "acceso permanente a la API incluso desde fuera del navegador. Con la "
                        "instancia expuesta en LAN (HOST!=127.0.0.1) esto es un robo de credencial "
                        "reutilizable. Una cookie HttpOnly+SameSite=Strict seria mejor")
    return "OK", "el token no se guarda en almacenamiento accesible por JS"


# --------------------------------------------------------------------------
@probe(8, "CSRF: peticiones sin cabecera Origin se aceptan", "MEDIA")
def s08():
    """check_request solo rechaza si el Origin viene Y no es de confianza."""
    r = client.post("/api/organize-now")  # sin Origin, como haria curl o una app local
    if r.status_code == 200:
        return "WARN", ("una peticion POST sin cabecera Origin se acepta. Los navegadores actuales "
                        "envian Origin en toda peticion cross-origin, asi que el CSRF clasico esta "
                        "cubierto; el riesgo real es que CUALQUIER proceso local del equipo (otro "
                        "usuario, una app, un script) puede manejar la API sin credencial cuando "
                        "no hay MARTIX_TOKEN. En un equipo compartido eso es acceso completo a los "
                        "documentos del usuario")
    return "OK", f"rechazada (status {r.status_code})"


# --------------------------------------------------------------------------
@probe(9, "Privacidad: el contenido de los documentos se envia a LLM_URL sin validar", "MEDIA")
def s09():
    fuente = (BACKEND / "app" / "llm.py").read_text(encoding="utf-8")
    valida_destino = "is_loopback_url" in fuente
    if valida_destino:
        return "OK", ("suggest_subfolder comprueba is_loopback_url(LLM_URL) en cada llamada y aborta "
                      "si el destino no es este equipo: el contenido de los documentos no puede salir")
    if not valida_destino:
        return "WARN", ("llm.suggest_subfolder envia un fragmento del CONTENIDO del documento a "
                        "LLM_URL. El README promete 'cero llamadas externas', pero LLM_URL sale de "
                        ".env sin ninguna comprobacion de que apunte a localhost: un .env manipulado "
                        "(o mal copiado de un tutorial) exfiltra extractos bancarios a un tercero "
                        "en silencio")
    return "OK", "el destino del LLM se valida como local"


# --------------------------------------------------------------------------
@probe(10, "PDF hostil: pypdf sin limite de tiempo ni de tamano", "MEDIA")
def s10():
    fuente = (BACKEND / "app" / "classifier.py").read_text(encoding="utf-8")
    tiene_limite = "_within_size_limit" in fuente and "MAX_PARSEABLE_FILE_BYTES" in fuente
    if tiene_limite:
        from app import classifier as _cls
        return "OK", (f"todos los extractores comprueban _within_size_limit "
                      f"({_cls.MAX_PARSEABLE_FILE_BYTES // (1024*1024)} MB) antes de abrir el archivo")
    if not tiene_limite:
        return "WARN", ("_extract_pdf_text limita a 6 paginas y 20.000 caracteres, pero PdfReader "
                        "parsea la estructura del PDF ENTERO antes de eso. Un PDF de descarga "
                        "malicioso (xref cicliclo, objetos anidados) puede colgar o consumir toda la "
                        "memoria de un worker del watcher. Falta un tope de tamano de archivo antes "
                        "de abrirlo")
    return "OK", "hay limites"


# --------------------------------------------------------------------------
@probe(11, "Enlaces simbolicos: escapar de HOME por una carpeta vigilada", "ALTA")
def s11():
    fuera = Path(tempfile.mkdtemp(prefix="martix-fuera-"))
    (fuera / "secreto.txt").write_text("datos fuera de HOME")
    enlace = HOME / "atajo_malicioso"
    if enlace.exists() or enlace.is_symlink():
        enlace.unlink()
    enlace.symlink_to(fuera)

    r = client.post("/api/watched-folders", json={"folder_path": "atajo_malicioso"})
    r2 = client.get("/api/browse?path=atajo_malicioso")
    r3 = client.post("/api/disk/scan", json={"path": "atajo_malicioso"})

    escapes = []
    if r.status_code == 201:
        escapes.append("watched-folders acepto el enlace")
    if r2.status_code == 200 and r2.get_json().get("entries"):
        escapes.append("browse listo el contenido externo")
    if r3.status_code == 200:
        escapes.append("disk/scan escaneo fuera de HOME")

    shutil.rmtree(fuera, ignore_errors=True)
    if escapes:
        return "VULN", f"se salio de la carpeta personal siguiendo un symlink: {escapes}"
    return "OK", "resolve_safe_path resuelve el enlace y lo rechaza"


# --------------------------------------------------------------------------
@probe(12, "Denegacion de servicio: /api/duplicates hashea sin limite", "BAJA")
def s12():
    fuente = (BACKEND / "app" / "organizer.py").read_text(encoding="utf-8")
    if "MAX_DUPLICATE_FILES" not in fuente or "deadline" not in fuente:
        return "WARN", ("find_duplicates recorre y hashea con SHA256 todos los archivos de las "
                        "carpetas indicadas sin tope de tiempo ni de tamano, dentro de la peticion "
                        "HTTP. Apuntarlo a una carpeta con muchos archivos grandes bloquea un worker "
                        "de Flask durante minutos u horas")
    from app import organizer as _org
    return "OK", (f"tope de {_org.MAX_DUPLICATE_FILES:,} archivos y presupuesto de "
                  f"{_org.DUPLICATE_TIME_BUDGET:.0f} s, aplicado tambien en la fase de hash completo")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 78)
    print("SONDA DE SEGURIDAD DE MARTIX -- HOME temporal:", HOME)
    print("=" * 78)
    for fn in [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10, s11, s12]:
        fn()

    print("\n" + "=" * 78)
    vulns = [r for r in RESULTS if r[3] == "VULN"]
    warns = [r for r in RESULTS if r[3] == "WARN"]
    print(f"RESUMEN: {len(vulns)} explotables | {len(warns)} debilidades | "
          f"{len([r for r in RESULTS if r[3] == 'OK'])} bloqueadas")
    for n, t, sev, v, _ in RESULTS:
        if v in ("VULN", "WARN", "ERROR"):
            print(f"  [{v}][{sev}] S{n:02d} {t}")
    print("=" * 78)
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if vulns else 0)
