#!/usr/bin/env python3
"""Pruebas de regresion de Martix: un caso por bug encontrado en la auditoria.

Aislada: HOME y base de datos temporales, no toca nada del usuario. Cada
comprobacion reproduce el fallo original y verifica que el arreglo sigue en
pie; si alguien revierte un arreglo, aqui vuelve a salir "BUG CONFIRMADO".

Ejecutar desde backend/:  .venv/bin/python tests/test_regressions.py
"""

import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="martix-probe-home-")
os.environ["HOME"] = _tmp
os.environ["USERPROFILE"] = _tmp

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from config import settings  # noqa: E402

FAKE_HOME = Path(_tmp).resolve()
settings.HOME_DIR = FAKE_HOME
settings.DOWNLOADS_DIR = FAKE_HOME / "Downloads"

from app import db  # noqa: E402
db.DB_PATH = FAKE_HOME / "probe.db"

from app import security, organizer, classifier, browser  # noqa: E402
from config.settings import is_temporary_download_file, is_file_in_use  # noqa: E402

DOWNLOADS = settings.DOWNLOADS_DIR
DOWNLOADS.mkdir(parents=True, exist_ok=True)

RESULTS = []


def probe(num, title):
    def deco(fn):
        def wrapper():
            try:
                verdict, detail = fn()
            except Exception as exc:
                import traceback
                verdict, detail = "ERROR", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            RESULTS.append((num, title, verdict, detail))
            mark = {"BUG": "\033[31mBUG CONFIRMADO\033[0m", "OK": "\033[32mOK\033[0m",
                    "ERROR": "\033[35mERROR EN SONDA\033[0m", "WARN": "\033[33mAVISO\033[0m"}[verdict]
            print(f"\n[P{num:02d}] {title}\n      -> {mark}: {detail}")
        return wrapper
    return deco


def fresh_downloads():
    for e in DOWNLOADS.iterdir():
        if e.is_dir():
            shutil.rmtree(e)
        else:
            e.unlink()


def clear_rules():
    with db.get_conn() as c:
        c.execute("DELETE FROM rules")
        c.execute("DELETE FROM topics")
        c.execute("DELETE FROM maintenance_rules")
        c.execute("DELETE FROM moves_log")


# --------------------------------------------------------------------------
@probe(1, "is_temporary_download_file: falsos positivos con '.part' en medio del nombre")
def p01():
    casos = ["pelicula.part1.rar", "backup.part2.rar", "datos.partition.csv",
             "informe.particular.pdf", "x.crdownload.pdf"]
    falsos = [c for c in casos if is_temporary_download_file(Path(c))]
    if falsos:
        # comprobar consecuencia real: organize_file no los mueve nunca
        fresh_downloads()
        f = DOWNLOADS / "backup.part2.rar"
        f.write_bytes(b"contenido real" * 100)
        res = organizer.organize_file(f)
        cons = "y organize_file los ignora (nunca se archivan)" if res is None else "pero organize_file si los movio"
        return "BUG", f"tratados como temporales: {falsos} {cons}"
    return "OK", "sin falsos positivos"


# --------------------------------------------------------------------------
@probe(2, "rules.extension UNIQUE: imposible tener 2 reglas condicionales de la misma extension")
def p02():
    clear_rules()
    db.add_rule("pdf", "Documents/Facturas", None,
                security.valid_conditions([{"field": "name", "operator": "contains", "value": "factura"}]))
    db.add_rule("pdf", "Documents/Contratos", None,
                security.valid_conditions([{"field": "name", "operator": "contains", "value": "contrato"}]))
    rules = [r for r in db.list_rules() if r["extension"] == "pdf"]
    if len(rules) == 1:
        return "BUG", (f"solo queda 1 regla pdf ({rules[0]['destination']}); la primera se sobrescribio "
                       "en silencio por el UNIQUE INDEX idx_rules_extension + ON CONFLICT DO UPDATE. "
                       "Toda la funcion de 'condiciones' es inutil para >1 regla por extension")
    return "OK", f"{len(rules)} reglas pdf coexisten"


# --------------------------------------------------------------------------
@probe(3, "valid_conditions rechaza operadores que check_conditions si implementa (gte/lte)")
def p03():
    implementados = {"contains", "not_contains", "equals", "starts_with", "ends_with",
                     "gt", "lt", "gte", "lte"}
    aceptados = security._VALID_CONDITION_OPERATORS
    faltan = implementados - aceptados
    if faltan:
        # confirmar que la API los rechaza
        r = security.valid_conditions([{"field": "size_kb", "operator": "gte", "value": 100}])
        return "BUG", (f"operadores implementados en organizer.check_conditions pero no permitidos por "
                       f"security.valid_conditions: {sorted(faltan)} -> valid_conditions devuelve {r!r} "
                       "(la API responde 400 'condiciones invalidas')")
    return "OK", "conjuntos coherentes"


# --------------------------------------------------------------------------
@probe(4, "_extract_docx_text trunca document.xml a 20.000 bytes -> XML invalido -> texto vacio")
def p04():
    fresh_downloads()
    docx = DOWNLOADS / "memoria.docx"
    parrafos = "".join(
        f'<w:p><w:r><w:t>Relleno de texto numero {i} para engordar el documento.</w:t></w:r></w:p>'
        for i in range(400)
    )
    xml = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>' + parrafos +
           '<w:p><w:r><w:t>PALABRACLAVEBANCO</w:t></w:r></w:p></w:body></w:document>')
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("word/document.xml", xml)
    tam = len(xml.encode())
    texto = classifier._extract_docx_text(docx)
    if tam > 20000 and texto == "":
        return "BUG", (f"document.xml de {tam} bytes (>20KB, normal en documentos reales) -> "
                       "f.read(20000) corta el XML, ET.fromstring lanza ParseError y se devuelve \"\". "
                       "La clasificacion por CONTENIDO de .docx no funciona nunca en documentos reales")
    return "OK", f"extraidos {len(texto)} chars de un xml de {tam} bytes"


# --------------------------------------------------------------------------
@probe(5, "is_file_in_use marca como 'en uso' cualquier archivo de solo lectura")
def p05():
    fresh_downloads()
    f = DOWNLOADS / "informe_solo_lectura.pdf"
    f.write_bytes(b"%PDF-1.4 contenido")
    os.chmod(f, 0o444)
    try:
        en_uso = is_file_in_use(f)
        res = organizer.organize_file(f)
        if en_uso:
            os.chmod(f, 0o644) if f.exists() else None
            return "BUG", ("un archivo 0444 (solo lectura, muy comun en adjuntos y medios montados) "
                           f"se reporta como 'en uso' porque is_file_in_use lo abre en modo 'r+b'; "
                           f"organize_file devolvio {res!r} -> nunca se archiva y el watcher "
                           "malgasta 300 ticks (5 min) esperando por el")
        return "OK", f"no se considera en uso; organize_file lo movio a {res['destination'] if res else None}"
    finally:
        if f.exists():
            os.chmod(f, 0o644)


# --------------------------------------------------------------------------
@probe(6, "undo de un 'desempaquetado' renombra la carpeta extraida a nombre.zip")
def p06():
    fresh_downloads()
    clear_rules()
    z = DOWNLOADS / "paquete.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("dentro/a.txt", "hola")
    res = organizer.organize_file(z)
    extraida = DOWNLOADS / "paquete"
    if not extraida.is_dir() or not (extraida / "dentro" / "a.txt").exists():
        return "BUG", f"el zip no se desempaqueto: {res!r}"
    if res is None:
        return "BUG", "el zip no se archivo tras desempaquetarlo"

    movimientos = db.recent_moves(5)
    extraccion = next((m for m in movimientos if m["category"] == "desempaquetado"), None)
    archivado = next((m for m in movimientos if m["category"] != "desempaquetado"), None)
    if extraccion is None or extraccion["undoable"] is not False:
        return "BUG", f"la extraccion deberia registrarse como no reversible: {extraccion!r}"
    if archivado is None or archivado["undoable"] is not True:
        return "BUG", f"el movimiento del zip deberia ser reversible: {archivado!r}"

    # El zip original sigue existiendo y su movimiento se puede deshacer
    undo_res, err = organizer.undo_move(archivado["id"])
    restaurado = DOWNLOADS / "paquete.zip"
    if err is not None:
        return "BUG", f"no se pudo deshacer el archivado del zip: {err}"
    if not restaurado.is_file():
        return "BUG", f"tras deshacer, 'paquete.zip' no es un archivo: existe={restaurado.exists()}"
    return "OK", ("el zip ya no se borra: se extrae en ./paquete/ (registrado como no reversible) y el "
                  ".zip se archiva con un movimiento normal que SI se puede deshacer, recuperando el "
                  "fichero original intacto")


# --------------------------------------------------------------------------
@probe(7, "format_rename_pattern con placeholders vacios produce nombres ocultos o vacios")
def p07():
    fresh_downloads()
    f = DOWNLOADS / "documento.pdf"
    f.write_bytes(b"x" * 50)
    n1 = organizer.format_rename_pattern("{Topic}", f, "documents", None)
    sin_ext = DOWNLOADS / "sinextension"
    sin_ext.write_bytes(b"x" * 50)
    n2 = organizer.format_rename_pattern("{Topic}", sin_ext, "documents", None)
    n3 = organizer.format_rename_pattern("{ARTIST} - {TITLE}", f, "documents", None)
    problemas = []
    if n1.startswith("."):
        problemas.append(f"'{{Topic}}' sin tema -> {n1!r} (archivo OCULTO sin nombre)")
    if n2 == "":
        problemas.append(f"'{{Topic}}' en archivo sin extension -> {n2!r} (nombre VACIO: "
                         "dest_dir / '' == dest_dir, shutil.move sobre el propio directorio destino)")
    if n3.strip(" -.") == "" or n3 == " - .pdf":
        problemas.append(f"'{{ARTIST}} - {{TITLE}}' sin metadatos -> {n3!r}")
    if problemas:
        return "BUG", ("no hay fallback cuando los placeholders se resuelven a vacio: "
                       + " | ".join(problemas))
    return "OK", f"{n1!r} {n2!r} {n3!r}"


# --------------------------------------------------------------------------
@probe(8, "create_app() borra archivos: lanza run_maintenance_cleanup en segundo plano")
def p08():
    clear_rules()
    victima_dir = FAKE_HOME / "Documents" / "Temporal"
    victima_dir.mkdir(parents=True, exist_ok=True)
    victima = victima_dir / "importante.txt"
    victima.write_text("datos del usuario")
    viejo = time.time() - 60 * 86400
    os.utime(victima, (viejo, viejo))
    db.add_maintenance_rule("Documents/Temporal", 30, 1)

    from app import server
    server.create_app()
    for _ in range(40):
        if not victima.exists():
            break
        time.sleep(0.05)
    if not victima.exists():
        return "BUG", ("crear la app Flask (create_app) lanza un hilo que ejecuta run_maintenance_cleanup "
                       "y BORRA archivos del usuario como efecto secundario de arrancar/importar. "
                       "Sin confirmacion, sin papelera y ademas duplicado con el scheduler, que "
                       "tambien ejecuta el mantenimiento inmediatamente al arrancar (last_run=0.0)")
    return "OK", "create_app no borro el archivo"


# --------------------------------------------------------------------------
@probe(9, "run_maintenance_cleanup borra sin papelera, incluye ocultos y no limpia carpetas vacias")
def p09():
    clear_rules()
    base = FAKE_HOME / "Documents" / "Barrido"
    sub = base / "sub" / "profunda"
    sub.mkdir(parents=True, exist_ok=True)
    oculto = base / ".config_importante"
    normal = sub / "viejo.log"
    oculto.write_text("config")
    normal.write_text("log")
    viejo = time.time() - 90 * 86400
    for p in (oculto, normal):
        os.utime(p, (viejo, viejo))
    db.add_maintenance_rule("Documents/Barrido", 30, 1)
    borrados = organizer.run_maintenance_cleanup()
    nombres = {b["filename"] for b in borrados}
    obs = []
    if ".config_importante" in nombres:
        obs.append("borra archivos OCULTOS (dotfiles de configuracion)")
    if sub.exists() and not any(sub.iterdir()):
        obs.append("deja el arbol de carpetas vacias sin limpiar")
    obs.append("usa unlink() directo: no hay papelera ni recuperacion posible")
    return ("BUG", "; ".join(obs)) if len(obs) > 1 else ("OK", str(nombres))


# --------------------------------------------------------------------------
@probe(10, "scan_disk_usage recurre sin limite: max_depth no corta la recursion")
def p10():
    from app import disk_analyzer
    hondo = FAKE_HOME / "Documents" / "hondo"
    p = hondo
    PROF = 60
    for i in range(PROF):
        p = p / f"n{i}"
    p.mkdir(parents=True, exist_ok=True)
    (p / "fondo.bin").write_bytes(b"z" * 1024)
    import sys as _sys
    max_pila = {"n": 0}

    def _perfil(frame, event, arg):
        if event == "call" and frame.f_code.co_name == "_scan_node":
            prof = 0
            f = frame
            while f:
                if f.f_code.co_name == "_scan_node":
                    prof += 1
                f = f.f_back
            max_pila["n"] = max(max_pila["n"], prof)
        return None

    _sys.setprofile(_perfil)
    try:
        res = disk_analyzer.scan_disk_usage(hondo, max_depth=3)
    finally:
        _sys.setprofile(None)

    conto = res["tree"]["files_count"] == 1
    if not conto:
        return "BUG", f"el archivo del fondo no se conto: files_count={res['tree']['files_count']}"
    if max_pila["n"] > 6:
        return "BUG", (f"la recursion llego a {max_pila['n']} marcos con max_depth=3 "
                       f"(arbol de {PROF} niveles)")
    return "OK", (f"tamano correcto (files_count=1) con solo {max_pila['n']} marcos de recursion "
                  f"sobre un arbol de {PROF} niveles: por debajo de max_depth se usa el "
                  f"acumulador iterativo. truncated={res.get('truncated')}")


# --------------------------------------------------------------------------
@probe(11, "condicion 'content' en extensiones sin extractor: not_contains casa con todo")
def p11():
    fresh_downloads()
    f = DOWNLOADS / "video_confidencial.mp4"
    f.write_bytes(b"\x00" * 200)
    conds = security.valid_conditions([{"field": "content", "operator": "not_contains", "value": "secreto"}])
    casa = organizer.check_conditions(f, "mp4", conds)
    if casa:
        return "BUG", ("_extract_content devuelve \"\" para toda extension sin extractor (mp4, xlsx, zip...) "
                       "y 'not_contains' sobre \"\" es siempre cierto: una regla con extension '*' y "
                       "content not_contains X se traga TODOS los archivos binarios del sistema")
    return "OK", "no casa"


# --------------------------------------------------------------------------
@probe(12, "clean_destination rechaza carpetas legitimas que contengan ':'")
def p12():
    casos = ["Documents/Reunion 10:30", "Music/AC:DC"]
    rechazados = [c for c in casos if security.clean_destination(c) is None]
    if rechazados:
        return "WARN", (f"rechazados por el filtro anti-unidad-Windows (':' in text): {rechazados}. "
                        "En Linux/macOS son nombres validos. Solo deberia rechazarse un ':' en la "
                        "posicion 2 (patron 'C:')")
    return "OK", "aceptados"


# --------------------------------------------------------------------------
@probe(13, "history: movimientos de mantenimiento (destination='DELETED') ofrecen 'Deshacer' roto")
def p13():
    clear_rules()
    db.log_move("borrado.log", str(FAKE_HOME / "x/borrado.log"),
                "papelera:quarantine", "mantenimiento", undoable=False)
    fila = db.recent_moves(1)[0]
    res, err = organizer.undo_move(fila["id"])
    if fila["undoable"] is not False:
        return "BUG", "la fila de mantenimiento no viene marcada como no reversible"
    if res is not None:
        return "BUG", "undo_move acepto deshacer un borrado de mantenimiento"
    if "papelera" not in (err or ""):
        return "BUG", f"mensaje de error poco util: {err!r}"
    return "OK", (f"la fila se marca undoable=False (la UI oculta el boton) y undo_move explica "
                  f"la via correcta: {err!r}")


# --------------------------------------------------------------------------
@probe(14, "codigo muerto en server.py: _get_scan_dirs/_find_all_files/_scan_duplicates sin usar")
def p14():
    fuente = (BACKEND / "app" / "server.py").read_text(encoding="utf-8")
    muertas = []
    for nombre in ("_get_scan_dirs", "_find_all_files", "_scan_duplicates"):
        if fuente.count(nombre) == 1:
            muertas.append(nombre)
    if muertas:
        return "WARN", (f"definidas y nunca llamadas: {muertas}. _scan_duplicates ademas hashea entero "
                        "TODO archivo con tamano repetido (sin fast-hash), la version lenta que "
                        "organizer.find_duplicates ya sustituyo. Duplicacion de logica que se desincronizara")
    return "OK", "las tres funciones muertas se han eliminado de server.py"


# --------------------------------------------------------------------------
@probe(15, "escapeHtml del frontend no escapa comillas -> inyeccion en atributos HTML")
def p15():
    js = (BACKEND.parent / "frontend" / "app.js").read_text(encoding="utf-8")
    definicion_insegura = 'div.textContent = text;\n    return div.innerHTML;' in js
    escapa_comillas = '.replace(/"/g, "&quot;")' in js and ".replace(/'/g, \"&#39;\")" in js
    usos_atributo = [l.strip() for l in js.splitlines() if '="${escapeHtml' in l]
    if not definicion_insegura and escapa_comillas:
        return "OK", ("escapeHtml escapa ahora & < > \" ' y ` , asi que es seguro tambien dentro "
                      f"de atributos entrecomillados ({len(usos_atributo)} usos en contexto de atributo)")
    if definicion_insegura and usos_atributo:
        return "BUG", ("escapeHtml() usa textContent->innerHTML, que escapa < > & pero NO comillas. "
                       f"Se usa dentro de atributos entrecomillados en {len(usos_atributo)} sitios, p.ej. "
                       f"{usos_atributo[0][:90]!r}. Un archivo/carpeta descargado con nombre "
                       "'x\" onmouseover=\"fetch(...)' escapa del atributo y ejecuta JS con acceso a "
                       "/api/disk/delete y /api/duplicates/clean (borrado arbitrario en ~)")
    return "OK", "escapado correcto en contexto de atributo"


# --------------------------------------------------------------------------
@probe(16, "/api/disk/delete y /api/duplicates/clean borran cualquier ruta de ~ sin verificar el escaneo")
def p16():
    fuente = (BACKEND / "app" / "server.py").read_text(encoding="utf-8")
    tiene_rmtree = "shutil.rmtree(resolved)" in fuente
    sin_confirmacion = "needs_confirmation" not in fuente
    usa_papelera = "trash.move_to_trash" in fuente
    protege = "_safe_delete_target" in fuente and "is_protected_path" in fuente
    if usa_papelera and protege and not sin_confirmacion and not tiene_rmtree:
        return "OK", ("todo borrado pasa por _safe_delete_target (rechaza rutas protegidas), va a la "
                      "papelera en vez de rmtree, y las carpetas grandes exigen confirmacion explicita")
    if tiene_rmtree and sin_confirmacion:
        return "WARN", ("/api/disk/delete acepta CUALQUIER ruta bajo ~ y hace shutil.rmtree recursivo "
                        "sin comprobar que provenga de un escaneo previo ni excluir carpetas criticas "
                        "(~/.ssh, ~/.config, ~/Documents entero). Un solo POST borra ~/Documents. "
                        "Sin papelera. Combinado con P15 es borrado remoto en un clic")
    return "OK", "acotado"


# --------------------------------------------------------------------------
@probe(17, "reglas: la extension comodin '*' con condiciones no puede coexistir con otra '*'")
def p17():
    clear_rules()
    db.add_rule("*", "Documents/Grandes", None,
                security.valid_conditions([{"field": "size_kb", "operator": "gt", "value": 10000}]))
    db.add_rule("*", "Documents/Viejos", None,
                security.valid_conditions([{"field": "age_days", "operator": "gt", "value": 365}]))
    comodines = [r for r in db.list_rules() if r["extension"] == "*"]
    if len(comodines) == 1:
        return "BUG", (f"solo sobrevive 1 regla comodin ({comodines[0]['destination']}): mismo UNIQUE "
                       "que P02. No se pueden combinar 'archivos grandes' y 'archivos viejos'")
    return "OK", f"{len(comodines)} comodines"


# --------------------------------------------------------------------------
@probe(18, "_ensure_schema se ejecuta en CADA conexion (4 PRAGMA + 2 SELECT por operacion)")
def p18():
    import sqlite3
    db.get_setting("warm", "up")  # asegurar esquema ya validado
    sentencias = []
    orig_connect = sqlite3.connect

    def espia(*a, **k):
        c = orig_connect(*a, **k)
        c.set_trace_callback(sentencias.append)
        return c

    sqlite3.connect = espia
    try:
        db.get_setting("duplicate_action", "suffix")
    finally:
        sqlite3.connect = orig_connect
    por_lectura = len(sentencias)
    if por_lectura >= 8:
        return "WARN", (f"leer UN ajuste ejecuta {por_lectura} sentencias SQL: get_conn() abre conexion, "
                        "fija 3 PRAGMA (incluido journal_mode=WAL, que es escritura) y _ensure_schema "
                        "revalida sqlite_master + 3 PRAGMA table_info. organize_file hace ~6 de estas "
                        "llamadas por archivo")
    return "OK", (f"{por_lectura} sentencias SQL para leer un ajuste "
                  f"({[x.strip()[:40] for x in sentencias]}); antes eran 10")


# --------------------------------------------------------------------------
@probe(19, "scheduler._run_loop hace busy-wait cada 0,5 s en vez de esperar el intervalo")
def p19():
    fuente = (BACKEND / "app" / "scheduler.py").read_text(encoding="utf-8")
    if "self._stop_event.wait(0.5)" in fuente:
        return "WARN", ("el bucle despierta 2 veces por segundo (172.800 despertares/dia) solo para "
                        "comparar time.time(); podria esperar directamente el intervalo restante. "
                        "Impide que la CPU baje a estados profundos: bateria en portatiles")
    return "OK", "espera eficiente"


# --------------------------------------------------------------------------
@probe(20, "notificaciones en Windows usan MessageBox (dialogo modal bloqueante)")
def p20():
    fuente = (BACKEND / "app" / "watcher.py").read_text(encoding="utf-8")
    if "System.Windows.Forms.MessageBox" in fuente:
        return "BUG", ("en Windows cada archivo organizado abre un MessageBox modal que exige un clic, "
                       "no una notificacion nativa. Organizar 30 descargas = 30 dialogos apilados "
                       "robando el foco. Deberia usar el toast de Windows (BurntToast / "
                       "Windows.UI.Notifications) o plyer")
    return "OK", "notificacion nativa"


# --------------------------------------------------------------------------
@probe(21, "el watcher no es recursivo: archivos que llegan a subcarpetas nunca se organizan")
def p21():
    fuente = (BACKEND / "app" / "watcher.py").read_text(encoding="utf-8")
    if "recursive=False" in fuente:
        return "WARN", ("observer.schedule(..., recursive=False): si un navegador crea "
                        "~/Downloads/algo/archivo.pdf (Drive descarga carpetas asi), el archivo interno "
                        "no dispara ningun evento. Solo se rescata si la carpeta padre se mueve entera")
    return "OK", "recursivo"


# --------------------------------------------------------------------------
@probe(22, "unpack_archive no limita el tamano descomprimido (zip bomb)")
def p22():
    fuente = (BACKEND / "app" / "organizer.py").read_text(encoding="utf-8")
    tiene_limite = any(k in fuente for k in ("file_size", "MAX_UNPACK", "shutil.disk_usage"))
    if not tiene_limite:
        fresh_downloads()
        bomba = DOWNLOADS / "bomba.zip"
        with zipfile.ZipFile(bomba, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("grande.bin", b"\x00" * (20 * 1024 * 1024))
        ratio = (20 * 1024 * 1024) / bomba.stat().st_size
        return "WARN", (f"se valida Zip-Slip pero no el tamano: un zip de {bomba.stat().st_size} bytes "
                        f"se expande x{ratio:.0f} sin control. Un .zip descargado automaticamente puede "
                        "llenar el disco. Falta comprobar sum(m.file_size) contra disk_usage().free")
    return "OK", "limitado"


# --------------------------------------------------------------------------
@probe(23, "organize_file: OSError sin capturar si el destino desaparece entre exists() y stat()")
def p23():
    fuente = (BACKEND / "app" / "organizer.py").read_text(encoding="utf-8")
    frag = "if destination.stat().st_size == path.stat().st_size and calculate_sha256"
    if frag in fuente and "try" not in fuente.split("if destination.exists():")[1][:80]:
        return "WARN", ("destination.stat() se llama fuera de try: si otro proceso (o uno de los 4 "
                        "workers del watcher) borra el destino justo despues de exists(), salta "
                        "FileNotFoundError sin capturar y muere el worker del watcher "
                        "(el hilo imprime el error pero el archivo se pierde de la cola)")
    return "OK", "protegido"


# --------------------------------------------------------------------------
@probe(24, "el handler del watcher arranca 4 hilos al IMPORTAR server.py, aunque la patrulla este apagada")
def p24():
    import threading
    fuente = (BACKEND / "app" / "server.py").read_text(encoding="utf-8")
    nivel_modulo = "\npatrol = PatrolManager(DOWNLOADS_DIR)" in fuente
    workers = [t for t in threading.enumerate() if t.name.startswith("Thread-")]
    if nivel_modulo:
        return "WARN", ("`patrol = PatrolManager(...)` a nivel de modulo construye "
                        "_DownloadEventHandler(), que en su __init__ lanza 4 hilos worker permanentes. "
                        f"Con la patrulla apagada siguen vivos ({len(workers)} hilos genericos ahora). "
                        "Ademas impide testear server.py sin efectos secundarios")
    return "OK", "perezoso"


# --------------------------------------------------------------------------
@probe(25, "resolve_destination_folder recarga TODAS las reglas de la BD por cada archivo")
def p25():
    clear_rules()
    for i in range(5):
        db.add_rule(f"ex{i}", f"Documents/D{i}")
    llamadas = {"n": 0}
    orig = db.list_rules

    def contando():
        llamadas["n"] += 1
        return orig()

    db.list_rules = contando
    try:
        fresh_downloads()
        for i in range(10):
            f = DOWNLOADS / f"archivo{i}.txt"
            f.write_bytes(b"x" * 40)
        organizer.organize_directory(DOWNLOADS)
        n = llamadas["n"]
    finally:
        db.list_rules = orig
    if n >= 10:
        return "WARN", (f"{n} consultas list_rules() para 10 archivos: una conexion SQLite nueva "
                        "(+ revalidacion de esquema) por archivo. Con 'Organizar Ahora' sobre miles "
                        "de archivos es el cuello de botella. Cachear reglas por barrido lo arregla")
    return "OK", f"{n} consultas"


# --------------------------------------------------------------------------
@probe(26, "clasificacion por Tema ignora el contenido de PDF/DOCX en carpetas (classify_folder)")
def p26():
    fuente = (BACKEND / "app" / "classifier.py").read_text(encoding="utf-8")
    usada = fuente.count("detect_topic")
    if usada <= 1:
        return "WARN", ("detect_topic() esta definida pero nunca se llama: classify() reimplementa la "
                        "misma logica en linea. Dos copias que ya divergen (classify cachea `content` "
                        "para reutilizarlo con el LLM, detect_topic no). Codigo muerto que confunde")
    return "OK", "en uso"


# --------------------------------------------------------------------------
@probe(27, "organize_folder puede mover una carpeta VIGILADA (bucle de reorganizacion)")
def p27():
    clear_rules()
    fresh_downloads()
    vigilada = FAKE_HOME / "Escaneos"
    vigilada.mkdir(exist_ok=True)
    db.add_watched_folder(str(vigilada))
    sub = DOWNLOADS / "fotos_verano"
    sub.mkdir()
    (sub / "a.jpg").write_bytes(b"\xff\xd8\xff" + b"x" * 100)
    reservada = organizer.is_destination_or_reserved_dir(vigilada)
    if not reservada:
        return "BUG", ("is_destination_or_reserved_dir() consulta categorias y temas, pero NO la tabla "
                       "watched_folders: una carpeta que el usuario puso a vigilar puede ser clasificada "
                       "y movida por el propio Martix, dejando la vigilancia apuntando a una ruta "
                       "inexistente")
    return "OK", "protegida"


# --------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 78)
    print("SONDA DE BUGS DE MARTIX -- HOME temporal:", FAKE_HOME)
    print("=" * 78)
    for fn in [p01, p02, p03, p04, p05, p06, p07, p08, p09, p10, p11, p12, p13,
               p14, p15, p16, p17, p18, p19, p20, p21, p22, p23, p24, p25, p26, p27]:
        fn()

    print("\n" + "=" * 78)
    bugs = [r for r in RESULTS if r[2] == "BUG"]
    warns = [r for r in RESULTS if r[2] == "WARN"]
    oks = [r for r in RESULTS if r[2] == "OK"]
    errs = [r for r in RESULTS if r[2] == "ERROR"]
    print(f"RESUMEN: {len(bugs)} bugs confirmados | {len(warns)} avisos | {len(oks)} ok | {len(errs)} sondas rotas")
    for n, t, v, _ in RESULTS:
        if v in ("BUG", "ERROR"):
            print(f"  [{v}] P{n:02d} {t}")
    print("=" * 78)
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if (bugs or errs) else 0)
