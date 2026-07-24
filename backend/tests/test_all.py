#!/usr/bin/env python3
"""Pruebas de integracion de Martix. Autocontenidas: usan una carpeta
personal (HOME) y una base de datos temporales, sin tocar nada del usuario.

Ejecutar:  ./.venv/bin/python tests/test_all.py   (desde backend/)
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# HOME falso ANTES de importar nada de Sortix (settings lee Path.home()
# en el momento del import).
_tmp = tempfile.mkdtemp(prefix="sortix-test-home-")
os.environ["HOME"] = _tmp
os.environ["USERPROFILE"] = _tmp  # equivalente en Windows

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from config import settings  # noqa: E402

FAKE_HOME = Path(_tmp).resolve()
assert settings.HOME_DIR.resolve() == FAKE_HOME, settings.HOME_DIR
assert settings.DOWNLOADS_DIR == FAKE_HOME / "Downloads"

from app import db, security  # noqa: E402

# la BD tambien va a la carpeta temporal, no a database/martix.db
db.DB_PATH = FAKE_HOME / "martix-test.db"

from app.organizer import organize_directory  # noqa: E402

# ---- validacion de destinos ----
cd = security.clean_destination
assert cd("Documents/Banco") == "Documents/Banco"
assert cd("  Docs/./Sub//x  ") == "Docs/Sub/x"
assert cd("Docs\\Sub") == "Docs/Sub"
assert cd("../x") is None
assert cd("Docs/../../x") is None
assert cd("/etc/passwd") is None
assert cd("C:\\Windows") is None
assert cd("C:/Windows") is None
assert cd("") is None
assert cd("..") is None
print("OK validacion de destinos")

ve = security.valid_extension
assert ve("pdf") == "pdf"
assert ve(".PDF") == "pdf"
assert ve("p df") is None
assert ve("") is None
assert ve("pdf/../x") is None
print("OK validacion de extensiones")

# ---- migracion: BD antigua sin undone_at ni el resto de tablas ----
old = sqlite3.connect(db.DB_PATH)
old.execute("""CREATE TABLE moves_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
    source TEXT NOT NULL, destination TEXT NOT NULL, category TEXT NOT NULL,
    moved_at TEXT NOT NULL DEFAULT (datetime('now')))""")
old.commit(); old.close()
db.init_db()
with db.get_conn() as conn:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(moves_log)")}
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert "undone_at" in cols, cols
assert {"rules", "settings", "topics", "maintenance_rules"} <= tables, tables
print("OK migracion y regeneracion de esquema")

# ---- app y guardas HTTP ----
from app.server import create_app  # noqa: E402

app = create_app()
client = app.test_client()

r = client.get("/api/status")
assert r.status_code == 200, r.data
r = client.get("/api/status", headers={"Host": "evil.example.com"})
assert r.status_code == 403, (r.status_code, r.data)
r = client.post("/api/organize-now", headers={"Origin": "https://evil.example.com"})
assert r.status_code == 403, (r.status_code, r.data)
r = client.post("/api/organize-now", headers={"Origin": "http://127.0.0.1:5000"})
assert r.status_code == 200, (r.status_code, r.data)
print("OK guardas Host/Origin")

# ---- validacion en la API ----
r = client.post("/api/rules", json={"extension": "pdf", "destination": "../../etc"})
assert r.status_code == 400, (r.status_code, r.data)
r = client.post("/api/rules", json={"extension": "p!f", "destination": "Docs"})
assert r.status_code == 400
r = client.post("/api/topics", json={"name": "Banco", "destination": "/etc", "keywords": "banco"})
assert r.status_code == 400
r = client.post("/api/topics", json={"name": "Banco", "destination": "Documents/Banco", "keywords": "banco, extracto, iban"})
assert r.status_code == 201, r.data
print("OK validacion API")

# ---- organizar: imagen a Pictures/Descargas ----
downloads = settings.DOWNLOADS_DIR
downloads.mkdir(parents=True, exist_ok=True)
(downloads / "foto.jpg").write_bytes(b"x" * 10)
moved = organize_directory(downloads)
assert len(moved) == 1, moved
dest = Path(moved[0]["destination"])
assert dest == FAKE_HOME / "Pictures/foto.jpg", dest
assert dest.exists() and not (downloads / "foto.jpg").exists()

# ---- tema por nombre de archivo ----
(downloads / "extracto_enero.pdf").write_bytes(b"%PDF-1.4 fake")
moved = organize_directory(downloads)
assert len(moved) == 1 and "Banco" in moved[0]["destination"], moved
print("OK organizacion basica y por Tema")

# ---- subcategorias descriptivas por nombre ----
(downloads / "Screenshot 2026-07-19 at 10.00.00.png").write_bytes(b"png")
(downloads / "factura_luz_enero.pdf").write_bytes(b"%PDF-1.4 fake")
(downloads / "notas sueltas.txt").write_bytes(b"apuntes varios sin nada especial")
moved = organize_directory(downloads)
dests = {m["filename"]: m["destination"] for m in moved}
assert dests["Screenshot 2026-07-19 at 10.00.00.png"].endswith(
    "Pictures/Screenshots/Screenshot 2026-07-19 at 10.00.00.png"), dests
assert "Documents/Invoices and receipts" in dests["factura_luz_enero.pdf"], dests
assert "Documents/Unclassified" in dests["notas sueltas.txt"], dests
print("OK subcategorias descriptivas")

# ---- LLM local: apagado por defecto y sanitizacion estricta ----
from app import llm  # noqa: E402

assert llm.suggest_subfolder("x.pdf", "contenido", "Documents") is None  # desactivado
s = llm._sanitize_folder_name
assert s("Recetas") == "Recetas"
assert s('  "Apuntes de fisica".  ') == "Apuntes de fisica"
assert s("../etc") is None
assert s("a/b") is None
assert s("C:evil") is None
assert s("") is None
assert s("x" * 60) is None
print("OK LLM apagado por defecto y sanitizacion")

# ---- anti-bucle: regla con destino = Downloads ----
r = client.post("/api/rules", json={"extension": "zip", "destination": "Downloads"})
assert r.status_code == 201
(downloads / "cosa.zip").write_bytes(b"zip")
moved = organize_directory(downloads)
assert moved == [], moved
assert (downloads / "cosa.zip").exists()
print("OK guarda anti-bucle (destino == origen)")

# ---- destino corrupto en BD: no se mueve, no explota ----
with db.get_conn() as conn:
    conn.execute("UPDATE rules SET destination = '../../fuera' WHERE extension = 'zip'")
moved = organize_directory(downloads)
assert moved == [], moved
assert (downloads / "cosa.zip").exists()
assert not (FAKE_HOME.parent / "fuera").exists()
print("OK defensa en profundidad con BD corrupta")

# ---- undo via API ----
r = client.get("/api/log?limit=100")
log = r.get_json()
move = next(m for m in log if m["filename"] == "foto.jpg")
r = client.post(f"/api/log/{move['id']}/undo")
assert r.status_code == 200, r.data
assert (downloads / "foto.jpg").exists()
assert not (FAKE_HOME / "Pictures/foto.jpg").exists()
r = client.post(f"/api/log/{move['id']}/undo")
assert r.status_code == 409, (r.status_code, r.data)
r = client.post("/api/log/99999/undo")
assert r.status_code == 409
print("OK undo (y doble undo rechazado)")

# ---- undo cuando el archivo ya no esta ----
move2 = next(m for m in client.get("/api/log?limit=100").get_json() if m["filename"] == "extracto_enero.pdf")
Path(move2["destination"]).unlink()
r = client.post(f"/api/log/{move2['id']}/undo")
assert r.status_code == 409
print("OK undo con archivo desaparecido")

# ---- cabeceras de privacidad ----
r = client.get("/api/log")
assert r.headers.get("Cache-Control") == "no-store"
assert r.headers.get("X-Content-Type-Options") == "nosniff"
print("OK cabeceras de privacidad")

# ---- token ----
security.API_TOKEN = "secreto123"
try:
    r = client.get("/api/status")
    assert r.status_code == 401
    r = client.get("/api/status", headers={"X-Martix-Token": "mal"})
    assert r.status_code == 401
    r = client.get("/api/status", headers={"X-Martix-Token": "secreto123"})
    assert r.status_code == 200
    r = client.get("/")  # el frontend se sirve sin token (no expone datos)
    assert r.status_code == 200
finally:
    security.API_TOKEN = ""
print("OK token de API")

# ---- browse no permite escaparse ----
r = client.get("/api/browse?path=../../etc")
assert r.status_code == 400
r = client.get("/api/browse?path=/etc")
assert r.status_code == 400
r = client.get("/api/browse?path=Downloads")
assert r.status_code == 200
print("OK browse confinado a HOME")

# ---- renombrado dinamico, condiciones de reglas y acciones de duplicados ----
# 1) Prueba de renombrado dinamico & condiciones
r = client.post("/api/rules", json={
    "extension": "*",
    "destination": "Documents/CustomRules",
    "rename_pattern": "Custom-{OriginalName}-{YYYY}.{ext}",
    "conditions": [{"field": "name", "operator": "contains", "value": "remito"}]
})
assert r.status_code == 201, r.data

(downloads / "mi_remito_luz.pdf").write_bytes(b"%PDF-1.4 fake")
moved = organize_directory(downloads)
moved_remito = [m for m in moved if m["filename"] == "mi_remito_luz.pdf"]
assert len(moved_remito) == 1, moved
dest = Path(moved_remito[0]["destination"])
import datetime
current_year = datetime.datetime.now().strftime("%Y")
assert dest.name == f"Custom-mi_remito_luz-{current_year}.pdf", dest.name

# 2) Prueba de duplicados: accion "delete_source"
db.set_setting("duplicate_action", "delete_source")
(downloads / "mi_remito_luz.pdf").write_bytes(b"%PDF-1.4 fake") # crear duplicado exacto en Downloads
assert (downloads / "mi_remito_luz.pdf").exists()
moved = organize_directory(downloads)
moved_remito = [m for m in moved if m["filename"] == "mi_remito_luz.pdf"]
assert len(moved_remito) == 0, moved
assert not (downloads / "mi_remito_luz.pdf").exists() # se elimino el origen duplicado!

# 3) Prueba de duplicados: accion "skip"
db.set_setting("duplicate_action", "skip")
(downloads / "mi_remito_luz.pdf").write_bytes(b"%PDF-1.4 fake") # crear duplicado exacto
moved = organize_directory(downloads)
moved_remito = [m for m in moved if m["filename"] == "mi_remito_luz.pdf"]
assert len(moved_remito) == 0, moved
assert (downloads / "mi_remito_luz.pdf").exists() # se omitio, el archivo sigue ahi

# Limpieza
db.set_setting("duplicate_action", "suffix")
(downloads / "mi_remito_luz.pdf").unlink()
print("OK renombrado dinamico, condiciones y duplicados")

# ---- mantenimiento ----
assert len(db.list_maintenance_rules()) == 0
mr = db.add_maintenance_rule("Downloads", 5, 1)
assert mr["directory_path"] == "Downloads"
assert mr["max_age_days"] == 5
assert mr["active"] == 1
rules = db.list_maintenance_rules()
assert len(rules) == 1
assert rules[0]["directory_path"] == "Downloads"
db.delete_maintenance_rule(mr["id"])
assert len(db.list_maintenance_rules()) == 0
print("OK maintenance rules helpers (new schema)")

# GET rules initially empty
r = client.get("/api/maintenance/rules")
assert r.status_code == 200, r.data
assert r.get_json() == []

# POST rule with unsafe path should fail
r = client.post("/api/maintenance/rules", json={"directory_path": "../unsafe", "max_age_days": 10})
assert r.status_code == 400, r.status_code
r = client.post("/api/maintenance/rules", json={"directory_path": "/etc/passwd", "max_age_days": 10})
assert r.status_code == 400, r.status_code

# POST rule with invalid max_age_days should fail
r = client.post("/api/maintenance/rules", json={"directory_path": "Downloads", "max_age_days": -5})
assert r.status_code == 400, r.status_code
r = client.post("/api/maintenance/rules", json={"directory_path": "Downloads", "max_age_days": "abc"})
assert r.status_code == 400, r.status_code
r = client.post("/api/maintenance/rules", json={"directory_path": "Downloads"})
assert r.status_code == 400, r.status_code

# POST valid rule
r = client.post("/api/maintenance/rules", json={"directory_path": "Downloads", "max_age_days": 2, "active": True})
assert r.status_code == 201, r.data
rule = r.get_json()
assert rule["directory_path"] == "Downloads"
assert rule["max_age_days"] == 2
assert rule["active"] is True

# GET rules should contain our rule now
r = client.get("/api/maintenance/rules")
assert r.status_code == 200, r.data
rules_list = r.get_json()
assert len(rules_list) == 1
assert rules_list[0]["directory_path"] == "Downloads"
assert rules_list[0]["active"] is True

rule_id = rule["id"]

# Crear archivos de prueba de distintas edades
import time
maint_dir = downloads / "MaintTest"
maint_dir.mkdir(parents=True, exist_ok=True)

file1 = maint_dir / "keep_fresh.txt"
file2 = maint_dir / "keep_recent.txt"
file3 = maint_dir / "delete_old.txt"

file1.write_text("fresh")
file2.write_text("recent")
file3.write_text("old")

now = time.time()
os.utime(file1, (now, now))
os.utime(file2, (now - 1.1 * 86400, now - 1.1 * 86400))
os.utime(file3, (now - 3.1 * 86400, now - 3.1 * 86400))

# Ejecutar el mantenimiento
r = client.post("/api/maintenance/run")
assert r.status_code == 200, r.data
resp = r.get_json()
assert resp["success"] is True
assert resp["deleted"] == 1
assert resp["items"][0]["filename"] == "delete_old.txt"

# Verificar eliminaciones
assert file1.exists()
assert file2.exists()
assert not file3.exists()

# Verificar log de movimientos
moves = db.recent_moves(10)
maint_moves = [m for m in moves if m["category"] == "mantenimiento"]
assert len(maint_moves) == 1
assert maint_moves[0]["filename"] == "delete_old.txt"
assert maint_moves[0]["destination"] == "DELETED"

# Eliminar regla y limpiar
r = client.delete(f"/api/maintenance/rules/{rule_id}")
assert r.status_code == 204

if file1.exists():
    file1.unlink()
if file2.exists():
    file2.unlink()
if file3.exists():
    file3.unlink()
if maint_dir.exists():
    maint_dir.rmdir()

print("OK maintenance rules execution, path safety, and API")

# ---- pruebas de endpoints de duplicados ----
(downloads / "dup1.pdf").write_bytes(b"contenido_duplicado_123")
(downloads / "dup2.pdf").write_bytes(b"contenido_duplicado_123")
(downloads / "unico.pdf").write_bytes(b"contenido_unico_456")
(downloads / "diferente_mismo_tamano.pdf").write_bytes(b"diferente_mismo_tamanx")

try:
    r = client.get("/api/duplicates")
    assert r.status_code == 200
    dups = r.get_json()
    
    group = next((g for g in dups if g["size_bytes"] == 23), None)
    assert group is not None, dups
    
    files_in_group = [f["name"] for f in group["files"]]
    assert "dup1.pdf" in files_in_group
    assert "dup2.pdf" in files_in_group
    assert "unico.pdf" not in files_in_group
    assert "diferente_mismo_tamano.pdf" not in files_in_group
    
    r = client.post("/api/duplicates/clean", json=["../../etc/passwd"])
    assert r.status_code == 400
    
    dup1_entry = next(f for f in group["files"] if f["name"] == "dup1.pdf")
    dup1_rel_path = dup1_entry["path"]
    
    r = client.post("/api/duplicates/clean", json=[dup1_rel_path])
    assert r.status_code == 200
    assert r.get_json() == {"success": True, "deleted": 1}
    
    assert not (downloads / "dup1.pdf").exists()
    assert (downloads / "dup2.pdf").exists()

finally:
    for fn in ("dup1.pdf", "dup2.pdf", "unico.pdf", "diferente_mismo_tamano.pdf"):
        p = downloads / fn
        if p.exists():
            p.unlink()

print("OK endpoints de duplicados y limpieza")

# ---- carpetas vigiladas ----
r = client.post("/api/watched-folders", json={"folder_path": "../../etc"})
assert r.status_code == 400, (r.status_code, r.data)
r = client.post("/api/watched-folders", json={})
assert r.status_code == 400
extra_dir = FAKE_HOME / "Escritorio"
extra_dir.mkdir(exist_ok=True)
r = client.post("/api/watched-folders", json={"folder_path": str(extra_dir)})
assert r.status_code == 201, (r.status_code, r.data)
wf = r.get_json()
assert wf["folder_path"] == str(extra_dir.resolve()), wf
r = client.get("/api/watched-folders")
assert r.status_code == 200
listed = r.get_json()
assert any(f["id"] == wf["id"] for f in listed), listed

# organize-now tambien recoge la carpeta vigilada
(extra_dir / "foto_vigilada.jpg").write_bytes(b"jpg")
r = client.post("/api/organize-now")
assert r.status_code == 200
assert not (extra_dir / "foto_vigilada.jpg").exists()

r = client.delete(f"/api/watched-folders/{wf['id']}")
assert r.status_code == 204
r = client.get("/api/watched-folders")
assert all(f["id"] != wf["id"] for f in r.get_json())
print("OK carpetas vigiladas")

# ---- simulacion (dry run) ----
sim_file = downloads / "simulada.jpg"
sim_file.write_bytes(b"jpg")
try:
    r = client.post("/api/simulate")
    assert r.status_code == 200
    sims = r.get_json()
    assert isinstance(sims, list), sims
    entry = next((s for s in sims if s["filename"] == "simulada.jpg"), None)
    assert entry is not None, sims
    assert entry["would_move_to"], entry
    assert sim_file.exists()  # dry run: no mueve nada
finally:
    if sim_file.exists():
        sim_file.unlink()
print("OK simulacion dry-run")

# ---- estadisticas ----
r = client.get("/api/statistics")
assert r.status_code == 200
stats = r.get_json()
assert set(stats) == {"total_organized", "by_category", "by_day"}, stats
assert stats["total_organized"] >= 1, stats
assert all({"category", "c"} <= set(row) for row in stats["by_category"]), stats
days = [row["day"] for row in stats["by_day"]]
assert days == sorted(days), days  # orden ascendente para el grafico
print("OK estadisticas")

# ---- patrulla multi-carpeta en tiempo real y actualizaciones dinamicas ----
from app.server import patrol, scheduler

dir_a = FAKE_HOME / "VigiladaA"
dir_b = FAKE_HOME / "VigiladaB"
dir_a.mkdir(exist_ok=True)
dir_b.mkdir(exist_ok=True)

r_a = client.post("/api/watched-folders", json={"folder_path": str(dir_a)})
assert r_a.status_code == 201, r_a.data
wf_a = r_a.get_json()

r_b = client.post("/api/watched-folders", json={"folder_path": str(dir_b)})
assert r_b.status_code == 201, r_b.data
wf_b = r_b.get_json()

patrol.start()
assert patrol.is_active() is True

watched_dirs = patrol.get_watched_directories()
assert settings.DOWNLOADS_DIR.resolve() in watched_dirs, watched_dirs
assert dir_a.resolve() in watched_dirs, watched_dirs
assert dir_b.resolve() in watched_dirs, watched_dirs

# Actualizacion dinamica: anadir carpeta C mientras la patrulla esta activa
dir_c = FAKE_HOME / "VigiladaC"
dir_c.mkdir(exist_ok=True)
r_c = client.post("/api/watched-folders", json={"folder_path": str(dir_c)})
assert r_c.status_code == 201, r_c.data
wf_c = r_c.get_json()

watched_dirs_2 = patrol.get_watched_directories()
assert dir_c.resolve() in watched_dirs_2, watched_dirs_2

# Actualizacion dinamica: eliminar carpeta A mientras la patrulla esta activa
r_del = client.delete(f"/api/watched-folders/{wf_a['id']}")
assert r_del.status_code == 204

watched_dirs_3 = patrol.get_watched_directories()
assert dir_a.resolve() not in watched_dirs_3, watched_dirs_3

# Intento de path traversal al anadir carpeta vigilada debe ser rechazado
r_bad = client.post("/api/watched-folders", json={"folder_path": "../../etc"})
assert r_bad.status_code == 400, r_bad.status_code

patrol.stop()
assert patrol.is_active() is False
print("OK patrulla multi-carpeta y actualizaciones dinamicas")

# ---- programador de tareas (Task Scheduler) ----
# GET /api/scheduler/config
r_sched = client.get("/api/scheduler/config")
assert r_sched.status_code == 200, r_sched.data
cfg = r_sched.get_json()
assert "enabled" in cfg
assert "interval_minutes" in cfg

# POST /api/scheduler/config invalido
r_invalid = client.post("/api/scheduler/config", json={"interval_minutes": -10})
assert r_invalid.status_code == 400, r_invalid.status_code
r_invalid_str = client.post("/api/scheduler/config", json={"interval_minutes": "abc"})
assert r_invalid_str.status_code == 400, r_invalid_str.status_code

# POST /api/scheduler/config valido
r_update = client.post("/api/scheduler/config", json={"enabled": True, "interval_minutes": 30})
assert r_update.status_code == 200, r_update.data
cfg_updated = r_update.get_json()
assert cfg_updated["enabled"] is True
assert cfg_updated["interval_minutes"] == 30

# Verificacion de start/stop del scheduler
scheduler.start()
assert scheduler.is_running() is True
scheduler.stop()
assert scheduler.is_running() is False

# Prueba de ejecucion de barrido de tareas (run_now)
(dir_b / "doc_sched.pdf").write_bytes(b"%PDF-1.4 test scheduler")
res_run = scheduler.run_now()
assert isinstance(res_run, dict)
assert res_run["files_organized"] >= 1
assert not (dir_b / "doc_sched.pdf").exists()

# Limpieza de carpetas de prueba
client.delete(f"/api/watched-folders/{wf_b['id']}")
client.delete(f"/api/watched-folders/{wf_c['id']}")

print("OK programador de tareas (scheduler)")

# ---- Fase 2: age_days y descompresion segura (Zip-Slip) ----
from app.organizer import check_conditions, unpack_archive
import json
import zipfile
import tarfile
import io

# 1) Prueba de check_conditions con age_days
test_age_file = downloads / "age_test.txt"
test_age_file.write_text("hello age")
now_ts = time.time()
# Establecer fecha de modificacion a hace 10 dias
os.utime(test_age_file, (now_ts - 10 * 86400, now_ts - 10 * 86400))

cond_gt_5 = json.dumps([{"field": "age_days", "operator": "gt", "value": "5"}])
cond_lt_5 = json.dumps([{"field": "age_days", "operator": "lt", "value": "5"}])
cond_gte_10 = json.dumps([{"field": "age_days", "operator": "gte", "value": "10"}])
cond_lte_9 = json.dumps([{"field": "age_days", "operator": "lte", "value": "9"}])

assert check_conditions(test_age_file, "txt", cond_gt_5) is True
assert check_conditions(test_age_file, "txt", cond_lt_5) is False
assert check_conditions(test_age_file, "txt", cond_gte_10) is True
assert check_conditions(test_age_file, "txt", cond_lte_9) is False

test_age_file.unlink()
print("OK condicion age_days en check_conditions")

# 2) Descompresion segura de Zip y Tar + prevencion de Zip-Slip
archive_test_dir = downloads / "ArchiveTest"
archive_test_dir.mkdir(parents=True, exist_ok=True)

# 2a) Zip valido
valid_zip = archive_test_dir / "valid.zip"
with zipfile.ZipFile(valid_zip, "w") as zf:
    zf.writestr("inner.txt", "contenido zip valido")

extract_target_zip = archive_test_dir / "valid_extracted"
unpack_archive(valid_zip, extract_target_zip)
assert (extract_target_zip / "inner.txt").exists()
assert (extract_target_zip / "inner.txt").read_text() == "contenido zip valido"

# 2b) Tar valido
valid_tar = archive_test_dir / "valid.tar.gz"
with tarfile.open(valid_tar, "w:gz") as tf:
    ti = tarfile.TarInfo(name="inner_tar.txt")
    data = b"contenido tar valido"
    ti.size = len(data)
    tf.addfile(ti, io.BytesIO(data))

extract_target_tar = archive_test_dir / "valid_tar_extracted"
unpack_archive(valid_tar, extract_target_tar)
assert (extract_target_tar / "inner_tar.txt").exists()
assert (extract_target_tar / "inner_tar.txt").read_bytes() == b"contenido tar valido"

# 2c) Zip-Slip en ZIP
malicious_zip = archive_test_dir / "malicious.zip"
with zipfile.ZipFile(malicious_zip, "w") as zf:
    zf.writestr("../evil_zip.txt", "malicious payload")

try:
    unpack_archive(malicious_zip, archive_test_dir / "zip_out")
    assert False, "Zip-Slip en ZIP debio lanzar ValueError"
except ValueError as e:
    assert "Zip-Slip" in str(e)
assert not (archive_test_dir / "evil_zip.txt").exists()

# 2d) Zip-Slip en TAR
malicious_tar = archive_test_dir / "malicious.tar"
with tarfile.open(malicious_tar, "w") as tf:
    ti = tarfile.TarInfo(name="../evil_tar.txt")
    data = b"malicious payload"
    ti.size = len(data)
    tf.addfile(ti, io.BytesIO(data))

try:
    unpack_archive(malicious_tar, archive_test_dir / "tar_out")
    assert False, "Zip-Slip en TAR debio lanzar ValueError"
except ValueError as e:
    assert "Zip-Slip" in str(e)
assert not (archive_test_dir / "evil_tar.txt").exists()

shutil.rmtree(archive_test_dir)
print("OK descompresion segura de Zip/Tar y prevencion Zip-Slip")

# ---- Pruebas de Deduplicación Optimizada (Fast-Hash / Full Hash) y Rutas Arbitrarias ----
custom_dup_dir = downloads / "custom_dup_folder"
custom_dup_dir.mkdir(exist_ok=True)

# 1. Dos archivos de >128KB idénticos (mismo tamaño, mismo fast-hash, mismo full SHA256)
large_content_1 = b"A" * 70000 + b"MIDDLE1" + b"B" * 70000
large_content_2 = b"A" * 70000 + b"MIDDLE1" + b"B" * 70000

# 2. Un archivo con mismo tamaño y mismo fast-hash (primeros 64K y últimos 64K idénticos) pero diferente contenido intermedio
large_content_diff_mid = b"A" * 70000 + b"MIDDLE2" + b"B" * 70000

(custom_dup_dir / "large_dup1.bin").write_bytes(large_content_1)
(custom_dup_dir / "large_dup2.bin").write_bytes(large_content_2)
(custom_dup_dir / "large_diff_mid.bin").write_bytes(large_content_diff_mid)

try:
    # Probar endpoint POST /api/duplicates con la carpeta personalizada
    r = client.post("/api/duplicates", json={"directories": ["Downloads/custom_dup_folder"]})
    assert r.status_code == 200, (r.status_code, r.data)
    dups_custom = r.get_json()

    # Debe encontrar solo el grupo de los 2 archivos idénticos y descartar el que difiere en el medio
    assert len(dups_custom) == 1, dups_custom
    files_in_dup = [f["name"] for f in dups_custom[0]["files"]]
    assert "large_dup1.bin" in files_in_dup
    assert "large_dup2.bin" in files_in_dup
    assert "large_diff_mid.bin" not in files_in_dup

    # Probar ruta no permitida / insegura en POST /api/duplicates
    r_bad = client.post("/api/duplicates", json={"directories": ["../../etc"]})
    assert r_bad.status_code == 400
finally:
    shutil.rmtree(custom_dup_dir, ignore_errors=True)

print("OK deduplicación optimizada (fast-hash) y rutas arbitrarias")

# ---- Pruebas de Exportación e Importación de Reglas (JSON) ----
db.add_rule("exptest", "Documents/ExportTest", rename_pattern="{YYYY}_{OriginalName}.{ext}")
db.add_maintenance_rule("Downloads/ExpMaint", 20, 1)

# 1. Exportar
r_exp = client.get("/api/rules/export")
assert r_exp.status_code == 200
exported = r_exp.get_json()
assert "rules" in exported
assert "maintenance_rules" in exported

exp_rule = next((r for r in exported["rules"] if r["extension"] == "exptest"), None)
assert exp_rule is not None
assert exp_rule["destination"] == "Documents/ExportTest"

exp_maint = next((m for m in exported["maintenance_rules"] if "ExpMaint" in m["folder"]), None)
assert exp_maint is not None

# 2. Importar
import_payload = {
    "rules": [
        {"extension": "imptest", "destination": "Documents/ImportTest", "rename_pattern": "IMP_{OriginalName}.{ext}"}
    ],
    "maintenance_rules": [
        {"folder": "Downloads/ImpMaint", "max_age_days": 10, "active": True}
    ]
}

r_imp = client.post("/api/rules/import", json=import_payload)
assert r_imp.status_code == 200
res_imp = r_imp.get_json()
assert res_imp.get("success") is True
assert res_imp.get("imported_rules") == 1
assert res_imp.get("imported_maintenance_rules") == 1

# Verificar inserción en BD
imp_rule_db = db.get_rule_for_extension("imptest")
assert imp_rule_db is not None
assert imp_rule_db["destination"] == "Documents/ImportTest"

maint_rules_db = db.list_maintenance_rules()
imp_maint_db = next((m for m in maint_rules_db if "ImpMaint" in m["folder"]), None)
assert imp_maint_db is not None
assert imp_maint_db["max_age_days"] == 10

# Importar con payload inválido
r_invalid = client.post("/api/rules/import", json={"rules": "no es una lista"})
assert r_invalid.status_code == 400

print("OK exportacion e importacion de reglas JSON")

# ---- Pruebas de Notificaciones Nativas del Watcher ----
from unittest.mock import patch
from app.watcher import send_notification, _DownloadEventHandler

with patch("subprocess.Popen") as mock_popen:
    send_notification("Test Title", "Test Message")
    time.sleep(0.1)
    assert mock_popen.called

with patch("app.watcher.send_notification") as mock_send_notif:
    with patch.object(_DownloadEventHandler, "_wait_until_stable", return_value=True):
        handler = _DownloadEventHandler()
        test_file = downloads / "notif_test.txt"
        test_file.write_text("contenido notificacion test")
        
        with patch("app.watcher.organize_file", return_value={"filename": "notif_test.txt", "category": "documentos"}):
            handler._schedule(test_file)
            time.sleep(0.2)
            assert mock_send_notif.called
            call_args = mock_send_notif.call_args[0]
            assert call_args[0] == "Martix"
            assert "notif_test.txt" in call_args[1]

        if test_file.exists():
            test_file.unlink()

print("OK notificaciones nativas del watcher")

# ---- verificacion de build_desktop.py ----
import ast

build_script = BACKEND / "build_desktop.py"
assert build_script.exists(), f"build_desktop.py no existe en {build_script}"
script_content = build_script.read_text(encoding="utf-8")
assert len(script_content) > 0, "build_desktop.py esta vacio"
ast.parse(script_content, filename=str(build_script))
print("OK verificacion de build_desktop.py")

# ---- Smart Learning: /api/learn-correction ----
r = client.post("/api/learn-correction", json={})
assert r.status_code == 400, r.data

r = client.post("/api/learn-correction", json={"filename": "song.mp3", "to_folder": "Music"})
assert r.status_code == 200, r.data
data = r.get_json()
assert data["destination"] == "Music", data
assert data["conditions"][0]["field"] == "extension", data
assert data["conditions"][0]["value"] == ".mp3", data
print("OK api learn-correction")

# ---- Metadata extraction, conditions, and dynamic renaming ----
from PIL import Image
from mutagen.id3 import ID3, TPE1, TALB, TIT2, TDRC
from app.organizer import check_conditions, format_rename_pattern
import json

img_test = downloads / "test_photo.jpg"
img_obj = Image.new("RGB", (20, 20), color="blue")
exif_dict = img_obj.getexif()
exif_dict[271] = "Canon"
exif_dict[272] = "EOS R5"
exif_dict[306] = "2025:06:10 15:30:00"
img_obj.save(img_test, exif=exif_dict)

mp3_test = downloads / "test_song.mp3"
mp3_test.write_bytes(b"TAG" + b"\x00" * 125)
id3_obj = ID3()
id3_obj.add(TPE1(encoding=3, text="Daft Punk"))
id3_obj.add(TALB(encoding=3, text="Discovery"))
id3_obj.add(TIT2(encoding=3, text="One More Time"))
id3_obj.add(TDRC(encoding=3, text="2001"))
id3_obj.save(mp3_test)

# Test metadata condition evaluation
assert check_conditions(img_test, "jpg", json.dumps([{"field": "camera", "operator": "contains", "value": "Canon"}]))
assert not check_conditions(img_test, "jpg", json.dumps([{"field": "camera", "operator": "contains", "value": "Nikon"}]))
assert check_conditions(img_test, "jpg", json.dumps([{"field": "exif_date", "operator": "starts_with", "value": "2025"}]))

assert check_conditions(mp3_test, "mp3", json.dumps([{"field": "artist", "operator": "equals", "value": "Daft Punk"}]))
assert check_conditions(mp3_test, "mp3", json.dumps([{"field": "album", "operator": "contains", "value": "Discovery"}]))
assert check_conditions(mp3_test, "mp3", json.dumps([{"field": "title", "operator": "contains", "value": "One More"}]))
assert check_conditions(mp3_test, "mp3", json.dumps([{"field": "year", "operator": "gt", "value": "2000"}]))
print("OK evaluacion de condiciones con metadatos")

# Test dynamic renaming placeholders
rename_mp3 = format_rename_pattern("{ARTIST} - {ALBUM} - {TITLE} ({year}).{ext}", mp3_test, "Music", None)
assert rename_mp3 == "Daft Punk - Discovery - One More Time (2001).mp3", rename_mp3

rename_img = format_rename_pattern("{CAMERA}_{EXIF_DATE}.{ext}", img_test, "Pictures", None)
assert "Canon EOS R5" in rename_img, rename_img
assert "2025" in rename_img, rename_img
print("OK marcadores dinamicos de renombrado con metadatos")

# Test onboarded settings endpoint
r = client.get("/api/settings")
assert r.status_code == 200
data = r.get_json()
assert "onboarded" in data
r = client.post("/api/settings", json={"onboarded": True})
assert r.status_code == 200
data = r.get_json()
assert data["onboarded"] is True
r = client.get("/api/settings")
assert r.get_json()["onboarded"] is True
print("OK ajuste onboarded persistente")

# Test helper detection of temporary download files and zero-byte/locked files
from config.settings import is_temporary_download_file
from app.organizer import organize_file
assert is_temporary_download_file(Path("Unconfirmed 12345.crdownload"))
assert is_temporary_download_file(Path("file.zip.part"))
assert is_temporary_download_file(Path("drive-download-20260724.zip"))
assert not is_temporary_download_file(Path("document.pdf"))

# Ensure 0-byte file or temporary download file is NOT organized by organize_file
zero_byte_file = downloads / "drive-download-temp.zip"
zero_byte_file.write_bytes(b"")
assert organize_file(zero_byte_file) is None
assert zero_byte_file.exists()
zero_byte_file.unlink()
print("OK proteccion de descargas temporales y archivos de 0 bytes")

if img_test.exists(): img_test.unlink()
if mp3_test.exists(): mp3_test.unlink()

# ---- Pruebas del Analizador WizTree (/api/disk/drives, /api/disk/scan, /api/disk/delete) ----
r_drives = client.get("/api/disk/drives")
assert r_drives.status_code == 200, r_drives.data
drives_data = r_drives.get_json()
assert isinstance(drives_data, list)
assert len(drives_data) >= 1

# Probamos scan de la carpeta Downloads
r_scan = client.post("/api/disk/scan", json={"path": "Downloads"})
assert r_scan.status_code == 200, r_scan.data
scan_res = r_scan.get_json()
assert "disk_info" in scan_res
assert "tree" in scan_res
assert "extensions" in scan_res
assert "treemap" in scan_res

# Probamos eliminacion mediante /api/disk/delete
dummy_del_file = downloads / "disk_del_test.tmp"
dummy_del_file.write_text("para eliminar")
r_del = client.post("/api/disk/delete", json={"path": "Downloads/disk_del_test.tmp"})
assert r_del.status_code == 200, r_del.data
assert not dummy_del_file.exists()

print("OK analizador de espacio de disco (backend & endpoints)")

# Probamos organización de carpetas completas
test_folder = downloads / "Fotos_Vacaciones_2025"
test_folder.mkdir(parents=True, exist_ok=True)
(test_folder / "playa.png").write_bytes(b"dummy image content")
(test_folder / "hotel.jpg").write_bytes(b"dummy image content 2")

res_folder = organize_file(test_folder)
assert res_folder is not None
assert res_folder.get("is_dir") is True
assert res_folder["category"] == "pictures" or "Pictures" in res_folder["destination"]
assert not test_folder.exists()
assert Path(res_folder["destination"]).exists()
print("OK organizacion de carpetas completas")

print("\nTODAS LAS PRUEBAS PASARON")
