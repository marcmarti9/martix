"""Servidor web de Martix: sirve la interfaz (frontend/) y expone la API
que usa para controlar la Patrulla Activa, lanzar una organizacion manual,
gestionar reglas/Temas y deshacer movimientos del historial."""

import atexit
import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from app import browser, db, llm, security, trash
from app.organizer import (
    find_duplicates,
    invalidate_scan_dirs_cache,
    organize_directory_report,
    simulate_directory,
    undo_move,
)
from app.scheduler import scheduler
from app.watcher import PatrolManager
from config import settings as llm_settings
from config.settings import DOWNLOADS_DIR, PROJECT_DIR, HOST

logger = logging.getLogger("martix.server")

import sys

if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR)) / "frontend"
else:
    FRONTEND_DIR = PROJECT_DIR / "frontend"

patrol = PatrolManager(DOWNLOADS_DIR)

atexit.register(patrol.stop)
atexit.register(scheduler.stop)



# Tope de cuerpo de peticion: sin el, un POST de reglas o de rutas puede
# agotar la memoria del proceso.
MAX_REQUEST_BYTES = 2 * 1024 * 1024


def _safe_delete_target(raw_path) -> tuple[Path | None, tuple[dict, int] | None]:
    """Resuelve una ruta recibida de la interfaz para BORRARLA.

    Todo borrado pasa por aqui: valida que la ruta sea una cadena, que caiga
    dentro de la carpeta personal y que no sea una ruta protegida (~/.ssh,
    ~/.config, la propia base de datos de Martix...). Devuelve (ruta, error).
    """
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, ({"error": "ruta invalida"}, 400)

    resolved = browser.resolve_safe_path(raw_path)
    if resolved is None:
        return None, ({"error": f"ruta no permitida: {raw_path}"}, 400)

    if security.is_protected_path(resolved):
        logger.warning("intento de borrado sobre ruta protegida: %s", resolved)
        return None, ({
            "error": f"ruta protegida, Martix no la borrara: {raw_path}"
        }, 403)

    return resolved, None


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
        MAX_FORM_MEMORY_SIZE=256 * 1024,
        MAX_FORM_PARTS=100,
    )

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

        # Segunda linea de defensa frente a XSS: aunque un dia se cuele una
        # inyeccion en el DOM, no podra cargar scripts remotos ni exfiltrar
        # nada, porque solo se permite el propio origen y no hay destinos de
        # red externos. La interfaz es 100% local (sin CDNs), asi que esta
        # politica no rompe nada.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "form-action 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "object-src 'none'"
        )
        # Redundante con frame-ancestors para navegadores antiguos.
        response.headers["X-Frame-Options"] = "DENY"
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
        """Dry-run: preview direct and nested files without moving anything."""
        return jsonify(simulate_directory(DOWNLOADS_DIR))

    @app.post("/api/organize-now")
    def organize_now():
        report = organize_directory_report(DOWNLOADS_DIR)
        moved = list(report["items"])
        review = list(report["review"])
        skipped = list(report["skipped"])
        truncated = bool(report.get("truncated"))
        # Also organize files from all active watched folders
        try:
            watched = db.list_watched_folders()
            for wf in watched:
                if not wf["active"]:
                    continue
                folder_path = browser.resolve_safe_path(wf.get("folder_path", ""))
                if folder_path and folder_path.exists() and folder_path.is_dir():
                    watched_report = organize_directory_report(folder_path)
                    moved.extend(watched_report["items"])
                    review.extend(watched_report["review"])
                    skipped.extend(watched_report["skipped"])
                    truncated = truncated or bool(watched_report.get("truncated"))
        except Exception:
            logger.debug("watched folders not available yet, skipping")
        return jsonify({
            "moved": len(moved),
            "items": moved,
            "review": review,
            "review_count": len(review),
            "skipped": skipped,
            "skipped_count": len(skipped),
            "truncated": truncated,
            "cleanup_suggestions": db.list_cleanup_suggestions("pending"),
        })

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
        # Varias reglas pueden compartir extension: es lo que permite encadenar
        # condiciones distintas sobre el mismo tipo de archivo.
        rule = db.add_rule(extension, destination, rename_pattern, conditions)
        return jsonify(rule), 201

    @app.patch("/api/rules/<int:rule_id>")
    @app.put("/api/rules/<int:rule_id>")
    def edit_rule(rule_id: int):
        if db.get_rule(rule_id) is None:
            return jsonify({"error": "regla no encontrada"}), 404
        payload = request.get_json(silent=True) or {}
        updates = {}

        if "extension" in payload:
            extension = security.valid_extension(payload.get("extension") or "")
            if extension is None:
                return jsonify({"error": "extension invalida"}), 400
            updates["extension"] = extension
        if "destination" in payload:
            destination = security.clean_destination(payload.get("destination") or "")
            if destination is None:
                return jsonify({"error": "carpeta destino invalida"}), 400
            updates["destination"] = destination
        if "rename_pattern" in payload:
            updates["rename_pattern"] = (payload.get("rename_pattern") or "").strip() or None
        if "conditions" in payload:
            conditions_raw = payload.get("conditions")
            conditions = security.valid_conditions(conditions_raw) if conditions_raw else None
            if conditions_raw and conditions is None:
                return jsonify({"error": "condiciones invalidas"}), 400
            updates["conditions"] = conditions
        if "priority" in payload:
            try:
                updates["priority"] = max(1, min(int(payload["priority"]), 100000))
            except (TypeError, ValueError):
                return jsonify({"error": "priority debe ser un entero"}), 400

        return jsonify(db.update_rule(rule_id, **updates))

    @app.post("/api/rules/reorder")
    def reorder_rules():
        """Reordena las reglas: el orden decide cual gana cuando varias casan."""
        payload = request.get_json(silent=True) or {}
        raw_ids = payload.get("ids")
        if not isinstance(raw_ids, list) or not raw_ids:
            return jsonify({"error": "ids debe ser una lista de identificadores de regla"}), 400
        try:
            ids = [int(i) for i in raw_ids]
        except (TypeError, ValueError):
            return jsonify({"error": "ids debe contener solo numeros"}), 400
        known = {r["id"] for r in db.list_rules()}
        if not set(ids).issubset(known):
            return jsonify({"error": "alguna regla del listado no existe"}), 400
        return jsonify(db.reorder_rules(ids))

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
        invalidate_scan_dirs_cache()
        return jsonify(topic), 201

    @app.delete("/api/topics/<int:topic_id>")
    def remove_topic(topic_id: int):
        db.delete_topic(topic_id)
        invalidate_scan_dirs_cache()
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
        # No se puede entrar en carpetas protegidas (~/.ssh, ~/.config...):
        # sus nombres de archivo ya son informacion util para un atacante.
        if security.is_protected_path(resolved):
            return jsonify({"error": "carpeta protegida: Martix no muestra su contenido"}), 403
        if not resolved.exists():
            return jsonify({"path": raw_path, "exists": False, "entries": []})
        if not resolved.is_dir():
            return jsonify({"error": "la ruta no es una carpeta"}), 400
        return jsonify({
            "path": raw_path,
            "exists": True,
            "entries": browser.list_directory(resolved),
        })

    def _settings_payload():
        return {
            "duplicate_action": db.get_setting("duplicate_action", "suffix"),
            "cleanup_mode": db.get_setting("cleanup_mode", "notify"),
            "onboarded": db.get_setting("onboarded", "0") == "1",
            "unpack_archives": str(db.get_setting("unpack_archives", "true")).lower() in ("true", "1"),
            "watch_recursive": db.get_setting("watch_recursive", "0") == "1",
            "native_trash": trash.native_trash_available(),
            "pending_cleanup": len(db.list_cleanup_suggestions("pending", limit=500)),
        }

    @app.get("/api/settings")
    def get_settings():
        return jsonify(_settings_payload())

    @app.post("/api/settings")
    def update_settings():
        payload = request.get_json(silent=True) or {}
        if "duplicate_action" in payload:
            action = payload["duplicate_action"]
            if action in ("suffix", "skip", "delete_source"):
                db.set_setting("duplicate_action", action)
        if "cleanup_mode" in payload:
            mode = payload["cleanup_mode"]
            if mode in ("notify", "direct"):
                db.set_setting("cleanup_mode", mode)
        if "onboarded" in payload:
            db.set_setting("onboarded", "1" if payload["onboarded"] else "0")
        if "unpack_archives" in payload:
            db.set_setting("unpack_archives", "true" if payload["unpack_archives"] else "false")
        if "watch_recursive" in payload:
            db.set_setting("watch_recursive", "1" if payload["watch_recursive"] else "0")
            # Reprogramar las vigilancias para que el cambio surta efecto ya.
            patrol.update_watched_folders()
        return jsonify(_settings_payload())

    @app.get("/api/cleanup-suggestions")
    def get_cleanup_suggestions():
        status = request.args.get("status", "pending")
        if status not in {"pending", "dismissed", "deleted", "missing", "all"}:
            return jsonify({"error": "estado no valido"}), 400
        return jsonify(db.list_cleanup_suggestions(None if status == "all" else status))

    @app.post("/api/cleanup-suggestions/<int:suggestion_id>/dismiss")
    def dismiss_cleanup_suggestion(suggestion_id: int):
        suggestion = db.get_cleanup_suggestion(suggestion_id)
        if suggestion is None:
            return jsonify({"error": "sugerencia no encontrada"}), 404
        return jsonify(db.resolve_cleanup_suggestion(suggestion_id, "dismissed"))

    @app.post("/api/cleanup-suggestions/<int:suggestion_id>/delete")
    def delete_cleanup_suggestion(suggestion_id: int):
        suggestion = db.get_cleanup_suggestion(suggestion_id)
        if suggestion is None:
            return jsonify({"error": "sugerencia no encontrada"}), 404

        resolved = browser.resolve_safe_path(suggestion.get("path", ""))
        if resolved is None or security.is_protected_path(resolved):
            db.resolve_cleanup_suggestion(suggestion_id, "missing")
            return jsonify({"error": "ruta no permitida o protegida"}), 403
        if not resolved.exists():
            db.resolve_cleanup_suggestion(suggestion_id, "missing")
            return jsonify({"error": "el archivo ya no existe"}), 404
        if not resolved.is_file() or resolved.is_symlink():
            return jsonify({"error": "solo se pueden retirar archivos normales"}), 400

        try:
            outcome = trash.move_to_trash(resolved)
        except OSError as exc:
            logger.exception("no se pudo enviar la sugerencia a la papelera")
            return jsonify({"error": f"no se pudo enviar a la papelera: {exc}"}), 500

        updated = db.resolve_cleanup_suggestion(suggestion_id, "deleted")
        return jsonify({
            "success": True,
            "suggestion": updated,
            "trash_method": outcome["method"],
            "trash_id": outcome["entry_id"],
        })

    @app.get("/api/llm/status")
    def get_llm_status():
        return jsonify(llm.status())

    @app.post("/api/llm/test")
    def test_llm_connection():
        payload = request.get_json(silent=True) or {}
        url = (payload.get("url") or "").strip() or llm_settings.LLM_URL
        model = (payload.get("model") or "").strip() or llm_settings.LLM_MODEL

        # Anti-SSRF: este endpoint hace una peticion HTTP desde el servidor con
        # la URL que le pasen. Sin restringirlo a loopback, cualquiera con
        # acceso a la API puede usar Martix para sondear puertos de localhost y
        # de la red local y leer las respuestas.
        if not security.is_loopback_url(url):
            return jsonify({
                "ok": False,
                "error": "solo se permiten direcciones locales (127.0.0.1, ::1 o localhost): "
                         "Martix nunca hace peticiones fuera de tu equipo",
            }), 400

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
        invalidate_scan_dirs_cache()
        patrol.update_watched_folders()
        return jsonify(result), 201

    @app.delete("/api/watched-folders/<int:folder_id>")
    def remove_watched_folder(folder_id: int):
        db.delete_watched_folder(folder_id)
        invalidate_scan_dirs_cache()
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

        if not isinstance(files_to_delete, list):
            return jsonify({"error": "se esperaba una lista de rutas"}), 400
        if len(files_to_delete) > 5000:
            return jsonify({"error": "demasiados archivos en una sola peticion"}), 400

        resolved_paths = []
        for f_path in files_to_delete:
            resolved, error = _safe_delete_target(f_path)
            if error:
                return jsonify(error[0]), error[1]
            if resolved.exists():
                if not resolved.is_file() or resolved.is_symlink():
                    return jsonify({"error": f"la ruta no es un archivo: {f_path}"}), 400
                resolved_paths.append(resolved)

        deleted, failed = [], []
        for resolved_path in resolved_paths:
            try:
                # A la papelera: "es un duplicado" es una conclusion del hash,
                # y si el usuario se equivoca de casilla tiene que poder
                # recuperarlo.
                trash.move_to_trash(resolved_path)
                deleted.append(str(resolved_path))
            except OSError:
                logger.exception("no se pudo enviar a la papelera %s", resolved_path)
                failed.append(resolved_path.name)

        return jsonify({
            "success": not failed,
            "deleted": len(deleted),
            "failed": failed,
            "trashed": True,
        })

    @app.get("/api/trash")
    def get_trash():
        return jsonify({
            "native": trash.native_trash_available(),
            "items": trash.list_trash(),
        })

    @app.post("/api/trash/<entry_id>/restore")
    def restore_from_trash(entry_id: str):
        entry, error = trash.restore(entry_id)
        if error:
            return jsonify({"error": error}), 409
        return jsonify(entry)

    @app.delete("/api/trash/<entry_id>")
    def purge_trash_entry(entry_id: str):
        removed = trash.purge(entry_id=entry_id)
        return jsonify({"success": True, "purged": removed})

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

    # Borrar una carpeta desde el analizador de espacio se lleva por delante
    # todo su contenido: exige confirmacion explicita a partir de este numero
    # de archivos, para que un clic accidental (o un script inyectado) no pueda
    # vaciar una carpeta entera de golpe.
    CONFIRM_REQUIRED_ABOVE = 25

    @app.post("/api/disk/delete")
    def delete_disk_item():
        payload = request.get_json(silent=True) or {}
        resolved, error = _safe_delete_target(payload.get("path"))
        if error:
            return jsonify(error[0]), error[1]
        if not resolved.exists():
            return jsonify({"error": "la ruta ya no existe"}), 404
        if resolved.is_symlink():
            return jsonify({"error": "no se borran enlaces simbolicos"}), 400

        if resolved.is_dir():
            file_count = sum(len(files) for _root, _dirs, files in os.walk(resolved))
            if file_count > CONFIRM_REQUIRED_ABOVE and not payload.get("confirm"):
                return jsonify({
                    "error": "confirmacion requerida",
                    "needs_confirmation": True,
                    "file_count": file_count,
                    "path": payload.get("path"),
                }), 409

        try:
            outcome = trash.move_to_trash(resolved)
        except OSError as exc:
            logger.exception("Error al enviar a la papelera un elemento del disco")
            return jsonify({"error": f"No se pudo eliminar: {exc}"}), 500

        return jsonify({
            "success": True,
            "deleted": str(payload.get("path")),
            "trashed": True,
            "trash_method": outcome["method"],
            "trash_id": outcome["entry_id"],
        })

    @app.get("/api/version")
    def get_version():
        # Version information is local-only.  The old endpoint executed
        # ``git fetch`` from a UI request, which broke the zero-network
        # guarantee and was unusable in a frozen executable.
        return jsonify({"version": "2026.08.01", "commit": "", "packaged": bool(getattr(sys, "frozen", False))})

    @app.get("/api/update/check")
    def check_update():
        return jsonify({
            "update_available": False,
            "message": "Las actualizaciones se distribuyen con el instalador de Martix.",
            "network_disabled": True,
        })

    @app.post("/api/update/apply")
    def apply_update():
        return jsonify({
            "success": False,
            "message": "Las actualizaciones se instalan mediante un nuevo instalador.",
            "network_disabled": True,
        }), 410

    return app



def resume_patrol_if_needed() -> None:
    # La deteccion es local y rapida: si Ollama esta instalado y el equipo
    # tiene recursos, se habilita sin exigir una variable de entorno.
    try:
        llm.initialize()
    except Exception:
        logger.debug("no se pudo inicializar el clasificador LLM local", exc_info=True)
    if db.get_setting("patrol_active", "0") == "1":
        patrol.start()
    if db.get_setting("scheduler_enabled", "1") == "1":
        scheduler.start()

