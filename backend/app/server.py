"""Servidor web de Martix: sirve la interfaz (frontend/) y expone la API
que usa para controlar la Patrulla Activa, lanzar una organizacion manual,
gestionar reglas/Temas y deshacer movimientos del historial."""

import atexit
import logging
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory

from app import browser, db, llm, security
from app.organizer import find_duplicates, organize_directory, resolve_destination_folder, undo_move
from app.scheduler import scheduler
from app.watcher import PatrolManager
from config import settings as llm_settings
from config.settings import DOWNLOADS_DIR, IGNORED_SUFFIXES, PROJECT_DIR, HOST, PORT

logger = logging.getLogger("martix.server")

import sys

if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR)) / "frontend"
else:
    FRONTEND_DIR = PROJECT_DIR / "frontend"

patrol = PatrolManager(DOWNLOADS_DIR)

atexit.register(patrol.stop)
atexit.register(scheduler.stop)



def _get_scan_dirs():
    dirs = set()
    dirs.add(DOWNLOADS_DIR.resolve())
    try:
        from config.settings import load_categories
        categories = load_categories()["categories"]
        for cat in categories.values():
            folder_str = cat.get("folder")
            if folder_str:
                from app.security import safe_destination_dir
                resolved = safe_destination_dir(folder_str)
                if resolved and resolved.exists():
                    dirs.add(resolved.resolve())
    except Exception:
        pass
    try:
        for topic in db.list_topics():
            folder_str = topic.get("destination")
            if folder_str:
                from app.security import safe_destination_dir
                resolved = safe_destination_dir(folder_str)
                if resolved and resolved.exists():
                    dirs.add(resolved.resolve())
    except Exception:
        pass
    return list(dirs)


def _find_all_files(scan_dirs):
    import os
    from config.settings import IGNORED_SUFFIXES
    files = []
    seen_paths = set()
    for root_dir in scan_dirs:
        if not root_dir.exists() or not root_dir.is_dir():
            continue
        for root, dirs, filenames in os.walk(root_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in filenames:
                if f.startswith('.'):
                    continue
                if Path(f).suffix.lower() in IGNORED_SUFFIXES:
                    continue
                file_path = Path(root) / f
                try:
                    resolved = file_path.resolve()
                    if resolved not in seen_paths and resolved.is_file():
                        seen_paths.add(resolved)
                        files.append(resolved)
                except OSError:
                    continue
    return files


def _scan_duplicates(files):
    from datetime import datetime
    from app.organizer import calculate_sha256
    from config.settings import HOME_DIR
    by_size = {}
    for path in files:
        try:
            size = path.stat().st_size
            by_size.setdefault(size, []).append(path)
        except OSError:
            continue
            
    duplicate_groups = {}
    for size, paths in by_size.items():
        if size == 0:
            continue
        if len(paths) < 2:
            continue
        for path in paths:
            sha = calculate_sha256(path)
            if sha:
                try:
                    rel_path = str(path.relative_to(HOME_DIR.resolve())).replace("\\", "/")
                except ValueError:
                    rel_path = str(path).replace("\\", "/")
                
                try:
                    stat = path.stat()
                    mtime_str = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                except OSError:
                    mtime_str = ""

                entry = {
                    "path": rel_path,
                    "name": path.name,
                    "mtime": mtime_str
                }
                duplicate_groups.setdefault(sha, {
                    "hash": sha,
                    "size_bytes": size,
                    "files": []
                })["files"].append(entry)

    result = [
        g for g in duplicate_groups.values()
        if len(g["files"]) >= 2
    ]
    
    for g in result:
        g["files"].sort(key=lambda x: x["path"])
        
    result.sort(key=lambda g: g["size_bytes"], reverse=True)
    return result


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    @app.before_request
    def guard_request():
        rejection = security.check_request(request)
        if rejection is not None:
            payload, status = rejection
            return jsonify(payload), status
        return None

    @app.after_request
    def privacy_headers(response):
        # las respuestas de la API contienen nombres y rutas de archivos
        # personales: que ni el navegador ni proxies las cacheen.
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return exc
        logger.exception("error inesperado atendiendo %s", request.path)
        return jsonify({"error": "error interno de Martix"}), 500

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def frontend_assets(filename):
        return send_from_directory(FRONTEND_DIR, filename)

    @app.get("/api/status")
    def status():
        return jsonify({
            "active": patrol.is_active(),
            "files_organized": db.count_moves(),
            "downloads_dir": str(DOWNLOADS_DIR),
        })

    @app.post("/api/patrol/toggle")
    def toggle_patrol():
        payload = request.get_json(silent=True) or {}
        desired = payload.get("active")
        if desired is None:
            desired = not patrol.is_active()

        if desired:
            patrol.start()
        else:
            patrol.stop()

        db.set_setting("patrol_active", "1" if patrol.is_active() else "0")
        return jsonify({"active": patrol.is_active()})

    @app.post("/api/simulate")
    def simulate():
        """Dry-run: classify every file in DOWNLOADS_DIR without moving."""
        results = []
        if DOWNLOADS_DIR.exists():
            for entry in sorted(DOWNLOADS_DIR.iterdir()):
                if not entry.is_file() or entry.suffix.lower() in IGNORED_SUFFIXES:
                    continue
                category, relative_folder, _rename = resolve_destination_folder(entry)
                dest_dir = security.safe_destination_dir(relative_folder)
                results.append({
                    "filename": entry.name,
                    "current_path": str(entry),
                    "would_move_to": str(dest_dir / entry.name) if dest_dir else None,
                    "category": category,
                })
        return jsonify(results)

    @app.post("/api/organize-now")
    def organize_now():
        moved = organize_directory(DOWNLOADS_DIR)
        # Also organize files from all active watched folders
        try:
            watched = db.list_watched_folders()
            for wf in watched:
                if not wf["active"]:
                    continue
                folder_path = Path(wf["folder_path"])
                if folder_path.exists() and folder_path.is_dir():
                    moved.extend(organize_directory(folder_path))
        except Exception:
            logger.debug("watched folders not available yet, skipping")
        return jsonify({"moved": len(moved), "items": moved})

    @app.get("/api/rules")
    def get_rules():
        return jsonify(db.list_rules())

    @app.post("/api/rules")
    def create_rule():
        payload = request.get_json(silent=True) or {}
        extension = security.valid_extension(payload.get("extension") or "")
        destination = security.clean_destination(payload.get("destination") or "")
        rename_pattern = (payload.get("rename_pattern") or "").strip() or None
        conditions_raw = payload.get("conditions")
        conditions = security.valid_conditions(conditions_raw) if conditions_raw else None

        if extension is None:
            return jsonify({"error": "extension invalida (solo letras y numeros, ej. pdf, o * para comodin)"}), 400
        if destination is None:
            return jsonify({"error": "carpeta destino invalida: debe ser relativa a tu carpeta personal, ej. Documents/Facturas"}), 400
        if conditions_raw and conditions is None:
            return jsonify({"error": "condiciones invalidas: campo u operador no reconocido"}), 400
        rule = db.add_rule(extension, destination, rename_pattern, conditions)
        return jsonify(rule), 201

    @app.delete("/api/rules/<int:rule_id>")
    def remove_rule(rule_id: int):
        db.delete_rule(rule_id)
        return "", 204

    @app.post("/api/learn-correction")
    def learn_correction():
        payload = request.get_json(silent=True) or {}
        filename = payload.get("filename")
        to_folder = payload.get("to_folder")
        from_folder = payload.get("from_folder")

        if not filename or not to_folder:
            return jsonify({"error": "filename y to_folder son obligatorios"}), 400

        rule = llm.suggest_rule_from_correction(filename, to_folder, from_folder)
        return jsonify(rule), 200

    @app.get("/api/rules/export")
    def export_rules():
        rules = db.list_rules()
        m_rules = db.list_maintenance_rules()
        for r in m_rules:
            r["active"] = bool(r["active"])
        return jsonify({
            "rules": rules,
            "maintenance_rules": m_rules
        })

    @app.post("/api/rules/import")
    def import_rules():
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "Payload JSON invalido"}), 400

        if isinstance(payload, list):
            rules_data = payload
            maint_data = []
        elif isinstance(payload, dict):
            rules_data = payload.get("rules", [])
            maint_data = payload.get("maintenance_rules", [])
        else:
            return jsonify({"error": "Payload JSON invalido"}), 400

        if not isinstance(rules_data, list) or not isinstance(maint_data, list):
            return jsonify({"error": "Formato de reglas o reglas de mantenimiento invalido"}), 400

        imported_rules = 0
        imported_maint = 0

        for r in rules_data:
            if not isinstance(r, dict):
                continue
            ext = security.valid_extension(r.get("extension") or "")
            dest = security.clean_destination(r.get("destination") or "")
            if ext is None or dest is None:
                continue
            rename_pattern = (r.get("rename_pattern") or "").strip() or None
            conditions_raw = r.get("conditions")
            conditions = security.valid_conditions(conditions_raw) if conditions_raw else None
            if conditions_raw and conditions is None:
                continue
            db.add_rule(ext, dest, rename_pattern, conditions)
            imported_rules += 1

        for m in maint_data:
            if not isinstance(m, dict):
                continue
            folder = m.get("directory_path") or m.get("folder")
            max_age = m.get("max_age_days")
            if not folder or max_age is None:
                continue
            resolved = browser.resolve_safe_path(folder)
            if resolved is None:
                continue
            try:
                max_age_int = int(max_age)
                if max_age_int <= 0:
                    continue
            except (ValueError, TypeError):
                continue
            active_val = 1 if m.get("active", True) else 0
            db.add_maintenance_rule(browser._path_to_key(resolved), max_age_int, active_val)
            imported_maint += 1

        return jsonify({
            "success": True,
            "imported_rules": imported_rules,
            "imported_maintenance_rules": imported_maint
        }), 200

    @app.get("/api/log")
    def get_log():
        limit = request.args.get("limit", default=20, type=int)
        return jsonify(db.recent_moves(limit))

    @app.post("/api/log/<int:move_id>/undo")
    def undo_log_move(move_id: int):
        result, error = undo_move(move_id)
        if error:
            return jsonify({"error": error}), 409
        return jsonify(result)

    @app.get("/api/topics")
    def get_topics():
        return jsonify(db.list_topics())

    @app.post("/api/topics")
    def create_topic():
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        destination = security.clean_destination(payload.get("destination") or "")
        keywords = payload.get("keywords") or []
        rename_pattern = (payload.get("rename_pattern") or "").strip() or None
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",")]
        keywords = [k for k in keywords if k]

        if not name or len(name) > 80:
            return jsonify({"error": "el nombre del tema es obligatorio (max. 80 caracteres)"}), 400
        if destination is None:
            return jsonify({"error": "carpeta destino invalida: debe ser relativa a tu carpeta personal, ej. Documents/Banco"}), 400
        if not keywords:
            return jsonify({"error": "indica al menos una palabra clave"}), 400

        # Validacion de Path Traversal / Seguridad
        if browser.resolve_safe_path(destination) is None:
            return jsonify({"error": "Ruta de destino no permitida o insegura"}), 400

        topic = db.add_topic(name, destination, keywords, rename_pattern)
        return jsonify(topic), 201

    @app.delete("/api/topics/<int:topic_id>")
    def remove_topic(topic_id: int):
        db.delete_topic(topic_id)
        return "", 204

    @app.get("/api/tree")
    def get_tree():
        return jsonify(browser.build_tree())

    @app.get("/api/browse")
    def browse_folder():
        raw_path = request.args.get("path", "")
        resolved = browser.resolve_safe_path(raw_path)
        if resolved is None:
            return jsonify({"error": "ruta no permitida"}), 400
        if not resolved.exists():
            return jsonify({"path": raw_path, "exists": False, "entries": []})
        if not resolved.is_dir():
            return jsonify({"error": "la ruta no es una carpeta"}), 400
        return jsonify({
            "path": raw_path,
            "exists": True,
            "entries": browser.list_directory(resolved),
        })

    @app.get("/api/settings")
    def get_settings():
        return jsonify({
            "duplicate_action": db.get_setting("duplicate_action", "suffix"),
            "onboarded": db.get_setting("onboarded", "0") == "1",
        })

    @app.post("/api/settings")
    def update_settings():
        payload = request.get_json(silent=True) or {}
        if "duplicate_action" in payload:
            action = payload["duplicate_action"]
            if action in ("suffix", "skip", "delete_source"):
                db.set_setting("duplicate_action", action)
        if "onboarded" in payload:
            onboarded_val = "1" if payload["onboarded"] else "0"
            db.set_setting("onboarded", onboarded_val)
        return jsonify({
            "duplicate_action": db.get_setting("duplicate_action", "suffix"),
            "onboarded": db.get_setting("onboarded", "0") == "1",
        })

    @app.get("/api/llm/status")
    def get_llm_status():
        return jsonify({
            "enabled": llm_settings.LLM_ENABLED,
            "url": llm_settings.LLM_URL,
            "model": llm_settings.LLM_MODEL,
        })

    @app.post("/api/llm/test")
    def test_llm_connection():
        payload = request.get_json(silent=True) or {}
        url = (payload.get("url") or "").strip() or llm_settings.LLM_URL
        model = (payload.get("model") or "").strip() or llm_settings.LLM_MODEL

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return jsonify({"ok": False, "error": "URL invalida"}), 400

        try:
            import json as _json
            import urllib.request as _urlreq
            req = _urlreq.Request(url.rstrip("/") + "/api/tags")
            with _urlreq.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)})

        models = [m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)]
        model_found = any(m == model or m.startswith(model + ":") for m in models)
        return jsonify({"ok": True, "models": models, "model_found": model_found})

    @app.get("/api/watched-folders")
    def get_watched_folders():
        return jsonify(db.list_watched_folders())

    @app.post("/api/watched-folders")
    def add_watched_folder():
        payload = request.get_json(silent=True) or {}
        folder_path = (payload.get("folder_path") or "").strip()
        if not folder_path:
            return jsonify({"error": "folder_path es obligatorio"}), 400
        resolved = browser.resolve_safe_path(folder_path)
        if resolved is None:
            return jsonify({"error": "ruta no permitida o insegura"}), 400
        result = db.add_watched_folder(str(resolved))
        patrol.update_watched_folders()
        return jsonify(result), 201

    @app.delete("/api/watched-folders/<int:folder_id>")
    def remove_watched_folder(folder_id: int):
        db.delete_watched_folder(folder_id)
        patrol.update_watched_folders()
        return "", 204

    @app.get("/api/scheduler/config")
    def get_scheduler_config():
        return jsonify(scheduler.get_config())

    @app.post("/api/scheduler/config")
    @app.put("/api/scheduler/config")
    def update_scheduler_config():
        payload = request.get_json(silent=True) or {}
        if "enabled" in payload:
            scheduler.enabled = bool(payload["enabled"])
        elif "active" in payload:
            scheduler.enabled = bool(payload["active"])

        if "interval_minutes" in payload:
            val = payload["interval_minutes"]
            try:
                val_int = int(val)
                if val_int <= 0:
                    return jsonify({"error": "interval_minutes debe ser un entero positivo"}), 400
                scheduler.interval_minutes = val_int
            except (ValueError, TypeError):
                return jsonify({"error": "interval_minutes debe ser un entero positivo"}), 400
        elif "interval" in payload:
            val = payload["interval"]
            try:
                val_int = int(val)
                if val_int <= 0:
                    return jsonify({"error": "interval debe ser un entero positivo"}), 400
                scheduler.interval_minutes = val_int
            except (ValueError, TypeError):
                return jsonify({"error": "interval debe ser un entero positivo"}), 400

        if scheduler.enabled and not scheduler.is_running():
            scheduler.start()
        elif not scheduler.enabled and scheduler.is_running():
            scheduler.stop()

        return jsonify(scheduler.get_config())

    @app.post("/api/scheduler/run")
    @app.post("/api/scheduler/run-now")
    def run_scheduler_now():
        res = scheduler.run_now()
        return jsonify({"success": True, **res})

    @app.get("/api/statistics")
    def get_statistics():
        return jsonify(db.get_statistics())

    @app.route("/api/duplicates", methods=["GET", "POST"])
    def get_duplicates():
        scan_dirs = None
        if request.method == "POST":
            payload = request.get_json(silent=True) or {}
            if "directories" in payload and payload["directories"] is not None:
                raw_dirs = payload["directories"]
                if not isinstance(raw_dirs, list):
                    return jsonify({"error": "directories debe ser una lista"}), 400
                scan_dirs = []
                for d in raw_dirs:
                    if not isinstance(d, str):
                        return jsonify({"error": "Las rutas deben ser cadenas de texto"}), 400
                    resolved = browser.resolve_safe_path(d)
                    if resolved is None or not resolved.exists() or not resolved.is_dir():
                        return jsonify({"error": f"Ruta invalida o no permitida: {d}"}), 400
                    scan_dirs.append(resolved)
        duplicates = find_duplicates(directories=scan_dirs)
        return jsonify(duplicates)

    @app.post("/api/duplicates/clean")
    def clean_duplicates():
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            files_to_delete = payload.get("files") or []
        elif isinstance(payload, list):
            files_to_delete = payload
        else:
            files_to_delete = []

        resolved_paths = []
        for f_path in files_to_delete:
            resolved = browser.resolve_safe_path(f_path)
            if resolved is None:
                return jsonify({"error": f"ruta no permitida: {f_path}"}), 400
            
            if resolved.exists():
                if not resolved.is_file():
                    return jsonify({"error": f"la ruta no es un archivo: {f_path}"}), 400
                resolved_paths.append(resolved)

        deleted_count = 0
        for resolved_path in resolved_paths:
            try:
                resolved_path.unlink()
                deleted_count += 1
            except OSError as e:
                logger.exception("Error unlinking file %s", resolved_path)
                return jsonify({"error": f"no se pudo eliminar: {resolved_path.name}"}), 500
        
        return jsonify({"success": True, "deleted": deleted_count})

    @app.get("/api/maintenance/rules")
    @app.get("/api/maintenance")
    def get_maintenance_rules():
        rules = db.list_maintenance_rules()
        for r in rules:
            r["active"] = bool(r["active"])
        return jsonify(rules)

    @app.post("/api/maintenance/rules")
    @app.post("/api/maintenance")
    def create_maintenance_rule():
        payload = request.get_json(silent=True) or {}
        directory_path = payload.get("directory_path") or payload.get("folder")
        max_age_days = payload.get("max_age_days")
        active_val = payload.get("active", True)
        
        if not directory_path or not isinstance(directory_path, str):
            return jsonify({"error": "directory_path es obligatorio"}), 400
            
        resolved_path = browser.resolve_safe_path(directory_path)
        if resolved_path is None:
            return jsonify({"error": "Ruta no permitida o insegura"}), 400
            
        if max_age_days is None:
            return jsonify({"error": "max_age_days es obligatorio"}), 400
        
        try:
            max_age_days_int = int(max_age_days)
            if max_age_days_int <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({"error": "max_age_days debe ser un entero positivo"}), 400

        active = 1 if active_val else 0
        stored_path = browser._path_to_key(resolved_path)
        
        rule = db.add_maintenance_rule(stored_path, max_age_days_int, active)
        rule["active"] = bool(rule["active"])
        return jsonify(rule), 201

    @app.delete("/api/maintenance/rules/<int:rule_id>")
    @app.delete("/api/maintenance/<int:rule_id>")
    def remove_maintenance_rule(rule_id: int):
        db.delete_maintenance_rule(rule_id)
        return "", 204

    @app.post("/api/maintenance/run")
    def run_maintenance():
        from app.organizer import run_maintenance_cleanup
        deleted = run_maintenance_cleanup()
        return jsonify({"success": True, "deleted": len(deleted), "items": deleted}), 200

    @app.get("/api/disk/drives")
    def get_disk_drives():
        from app.disk_analyzer import get_available_drives
        return jsonify(get_available_drives())

    @app.post("/api/disk/scan")
    def scan_disk():
        from app.disk_analyzer import scan_disk_usage
        payload = request.get_json(silent=True) or {}
        raw_path = payload.get("path")
        target_path = browser.resolve_safe_path(raw_path) if raw_path else DOWNLOADS_DIR
        if target_path is None or not target_path.exists():
            return jsonify({"error": "Ruta no permitida o no existe"}), 400
        try:
            res = scan_disk_usage(target_path)
            return jsonify(res)
        except Exception as e:
            logger.exception("Error escaneando disco: %s", e)
            return jsonify({"error": f"Error al escanear disco: {e}"}), 500

    @app.post("/api/disk/delete")
    def delete_disk_item():
        payload = request.get_json(silent=True) or {}
        raw_path = payload.get("path")
        if not raw_path:
            return jsonify({"error": "Ruta obligatoria"}), 400
        resolved = browser.resolve_safe_path(raw_path)
        if resolved is None or not resolved.exists():
            return jsonify({"error": "Ruta invalida o no permitida"}), 400
        try:
            if resolved.is_file():
                resolved.unlink()
            elif resolved.is_dir():
                import shutil
                shutil.rmtree(resolved)
            return jsonify({"success": True, "deleted": str(raw_path)})
        except Exception as e:
            logger.exception("Error al eliminar elemento del disco: %s", e)
            return jsonify({"error": f"No se pudo eliminar: {e}"}), 500


    # Ejecucion del mantenimiento al iniciar el servidor
    import threading
    def start_background_maintenance():
        try:
            from app.organizer import run_maintenance_cleanup
            run_maintenance_cleanup()
        except Exception as e:
            logger.exception("Error en la ejecucion de mantenimiento al inicio: %s", e)

    threading.Thread(target=start_background_maintenance, daemon=True).start()

    return app



def resume_patrol_if_needed() -> None:
    if db.get_setting("patrol_active", "0") == "1":
        patrol.start()
    if db.get_setting("scheduler_enabled", "1") == "1":
        scheduler.start()

