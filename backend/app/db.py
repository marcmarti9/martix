"""Acceso a la base de datos SQLite: reglas del usuario, log de movimientos
y ajustes persistentes (p.ej. si la Patrulla Activa estaba encendida)."""

import sqlite3
import threading
from contextlib import contextmanager

from config.settings import DB_PATH, SCHEMA_PATH


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn():
        pass  # get_conn ya garantiza el esquema


# Validar el esquema en CADA conexion costaba 6 sentencias extra por operacion
# (2 SELECT sobre sqlite_master + 4 PRAGMA table_info), y organize_file abre
# ~6 conexiones por archivo. Se valida una vez por proceso y se repite solo si
# alguien borra o vacia la base de datos con el servidor en marcha.
_schema_lock = threading.Lock()
_schema_checked_for: str | None = None

_rules_cache: list[dict] | None = None
_rules_cache_lock = threading.Lock()

_topics_cache: list[dict] | None = None
_topics_cache_lock = threading.Lock()


def _invalidate_db_caches() -> None:
    global _rules_cache, _topics_cache
    with _rules_cache_lock:
        _rules_cache = None
    with _topics_cache_lock:
        _topics_cache = None


def _invalidate_schema_cache() -> None:
    global _schema_checked_for
    with _schema_lock:
        _schema_checked_for = None
    _invalidate_db_caches()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Crea las tablas si faltan y aplica las migraciones pendientes."""
    global _schema_checked_for
    with _schema_lock:
        if _schema_checked_for == str(DB_PATH):
            return

        # WAL es una propiedad persistente del fichero: basta fijarla una vez,
        # no en cada conexion (ademas es una escritura).
        conn.execute("PRAGMA journal_mode = WAL")

        required = {"rules", "moves_log", "settings", "topics",
                    "maintenance_rules", "watched_folders", "cleanup_suggestions"}
        existing = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if not required.issubset(existing):
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(conn)
        conn.commit()
        _schema_checked_for = str(DB_PATH)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _migrate_rules_table(conn: sqlite3.Connection) -> None:
    """Elimina el UNIQUE(extension) heredado y anade 'priority'.

    El indice unico impedia tener mas de una regla por extension, lo que
    dejaba sin sentido toda la funcion de condiciones: crear una segunda regla
    .pdf sobrescribia la primera en silencio.
    """
    cols = _table_columns(conn, "rules")
    if not cols:
        return

    if "priority" not in cols:
        conn.execute("ALTER TABLE rules ADD COLUMN priority INTEGER NOT NULL DEFAULT 100")

    has_unique = any(row["unique"] for row in conn.execute("PRAGMA index_list(rules)"))
    if not has_unique:
        return

    conn.execute("DROP INDEX IF EXISTS idx_rules_extension")
    if not any(row["unique"] for row in conn.execute("PRAGMA index_list(rules)")):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_extension ON rules(extension)")
        return

    # El indice unico venia de una restriccion de columna: hay que rehacer la
    # tabla conservando las reglas existentes.
    conn.execute("ALTER TABLE rules RENAME TO _rules_old")
    conn.execute("""
        CREATE TABLE rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extension TEXT NOT NULL,
            destination TEXT NOT NULL,
            rename_pattern TEXT,
            conditions TEXT,
            priority INTEGER NOT NULL DEFAULT 100,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        INSERT INTO rules (extension, destination, rename_pattern, conditions, priority, created_at)
        SELECT extension, destination, rename_pattern, conditions,
               COALESCE(priority, 100), COALESCE(created_at, datetime('now'))
        FROM _rules_old
    """)
    conn.execute("DROP TABLE _rules_old")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_extension ON rules(extension)")


def _migrate(conn: sqlite3.Connection) -> None:
    """Migraciones para bases de datos creadas con esquemas anteriores."""
    moves_cols = _table_columns(conn, "moves_log")
    if "undone_at" not in moves_cols:
        conn.execute("ALTER TABLE moves_log ADD COLUMN undone_at TEXT")
    if "undoable" not in moves_cols:
        conn.execute("ALTER TABLE moves_log ADD COLUMN undoable INTEGER NOT NULL DEFAULT 1")
        # Las filas antiguas de estas categorias nunca fueron reversibles.
        conn.execute(
            "UPDATE moves_log SET undoable = 0 "
            "WHERE category IN ('mantenimiento', 'desempaquetado') OR destination = 'DELETED'"
        )

    rules_cols = _table_columns(conn, "rules")
    if "rename_pattern" not in rules_cols:
        conn.execute("ALTER TABLE rules ADD COLUMN rename_pattern TEXT")
    if "conditions" not in rules_cols:
        conn.execute("ALTER TABLE rules ADD COLUMN conditions TEXT")
    _migrate_rules_table(conn)

    topics_cols = _table_columns(conn, "topics")
    if "rename_pattern" not in topics_cols:
        conn.execute("ALTER TABLE topics ADD COLUMN rename_pattern TEXT")

    existing_tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    if "maintenance_rules" in existing_tables:
        m_cols = _table_columns(conn, "maintenance_rules")
        if "folder" not in m_cols:
            conn.execute("DROP TABLE maintenance_rules")
            existing_tables.discard("maintenance_rules")
    if "maintenance_rules" not in existing_tables:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder TEXT NOT NULL UNIQUE,
                max_age_days INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

    if "watched_folders" not in existing_tables:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watched_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_path TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

    if "cleanup_suggestions" not in existing_tables:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cleanup_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                reason TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'cleanup',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                resolved_at TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cleanup_suggestions_status "
            "ON cleanup_suggestions(status, created_at)"
        )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_moves_log_undone_moved "
        "ON moves_log(undone_at, moved_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_moves_log_undone_category "
        "ON moves_log(undone_at, category)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rules_ext_priority "
        "ON rules(extension, priority)"
    )


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        try:
            _ensure_schema(conn)
        except sqlite3.Error:
            # La BD pudo ser borrada o corrompida en caliente: se reintenta una
            # vez desde cero antes de propagar el fallo.
            _invalidate_schema_cache()
            _ensure_schema(conn)
        yield conn
        conn.commit()
    except sqlite3.DatabaseError:
        conn.rollback()
        _invalidate_schema_cache()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---- reglas personalizadas -------------------------------------------------

# Orden de evaluacion de reglas. organizer.resolve_destination_folder aplica la
# PRIMERA que casa, asi que el orden es la semantica:
#   1. priority (la fija el usuario; menor = antes)
#   2. reglas de extension concreta antes que las comodin ("*"): por orden
#      ASCII "*" (42) iria primero y silenciaria toda regla especifica
#   3. reglas CON condiciones antes que las que no las tienen: son mas
#      especificas, y si no una regla ".pdf -> Documentos" sin condiciones
#      dejaria muerta a ".pdf que contiene factura -> Facturas"
#   4. id, para que el orden sea estable y reproducible
_RULES_ORDER = (
    "ORDER BY priority ASC, "
    "(extension = '*') ASC, "
    "(conditions IS NULL OR conditions = '') ASC, "
    "id ASC"
)


def list_rules() -> list[dict]:
    global _rules_cache
    with _rules_cache_lock:
        if _rules_cache is not None:
            return [dict(r) for r in _rules_cache]
    with get_conn() as conn:
        rows = conn.execute(f"SELECT * FROM rules {_RULES_ORDER}").fetchall()
        result = [dict(r) for r in rows]
        with _rules_cache_lock:
            _rules_cache = result
        return [dict(r) for r in result]


def get_rule(rule_id: int) -> dict | None:
    for r in list_rules():
        if r.get("id") == rule_id:
            return dict(r)
    return None


def add_rule(extension: str, destination: str, rename_pattern: str | None = None,
             conditions: str | None = None, priority: int | None = None) -> dict:
    """Crea una regla nueva. Varias reglas pueden compartir extension: es lo que
    permite encadenar condiciones distintas sobre el mismo tipo de archivo."""
    extension = extension.lower().lstrip(".").strip()
    destination = destination.strip().strip("/")
    try:
        with get_conn() as conn:
            if priority is None:
                row = conn.execute("SELECT COALESCE(MAX(priority), 99) + 1 AS p FROM rules").fetchone()
                priority = row["p"]
            cur = conn.execute(
                """INSERT INTO rules (extension, destination, rename_pattern, conditions, priority)
                   VALUES (?, ?, ?, ?, ?)""",
                (extension, destination, rename_pattern, conditions, int(priority)),
            )
            row = conn.execute("SELECT * FROM rules WHERE id = ?", (cur.lastrowid,)).fetchone()
            return dict(row)
    finally:
        _invalidate_db_caches()


def update_rule(rule_id: int, **fields) -> dict | None:
    """Actualiza campos concretos de una regla existente."""
    allowed = {"extension", "destination", "rename_pattern", "conditions", "priority"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_rule(rule_id)
    if "extension" in updates:
        updates["extension"] = str(updates["extension"]).lower().lstrip(".").strip()
    if "destination" in updates:
        updates["destination"] = str(updates["destination"]).strip().strip("/")
    if "priority" in updates:
        updates["priority"] = int(updates["priority"])

    assignments = ", ".join(f"{k} = ?" for k in updates)
    try:
        with get_conn() as conn:
            conn.execute(
                f"UPDATE rules SET {assignments} WHERE id = ?",
                (*updates.values(), rule_id),
            )
            row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
            return dict(row) if row else None
    finally:
        _invalidate_db_caches()


def reorder_rules(ordered_ids: list[int]) -> list[dict]:
    """Reasigna prioridades segun el orden recibido desde la interfaz."""
    try:
        with get_conn() as conn:
            for position, rule_id in enumerate(ordered_ids, start=1):
                conn.execute("UPDATE rules SET priority = ? WHERE id = ?", (position, int(rule_id)))
            rows = conn.execute(f"SELECT * FROM rules {_RULES_ORDER}").fetchall()
            return [dict(r) for r in rows]
    finally:
        _invalidate_db_caches()


def delete_rule(rule_id: int) -> None:
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    finally:
        _invalidate_db_caches()


def get_rule_for_extension(extension: str) -> dict | None:
    """Primera regla (por orden de evaluacion) de una extension concreta.
    Ahora puede haber varias; usa list_rules_for_extension si las quieres todas."""
    rules = list_rules_for_extension(extension)
    return rules[0] if rules else None


def list_rules_for_extension(extension: str) -> list[dict]:
    ext = extension.lower().lstrip(".")
    return [dict(r) for r in list_rules() if r.get("extension") == ext]


# ---- log de movimientos / estadisticas -------------------------------------

def log_move(filename: str, source: str, destination: str, category: str,
             undoable: bool = True) -> int:
    """Registra un movimiento. 'undoable=False' para eventos que no se pueden
    revertir (desempaquetados, borrados de mantenimiento): la interfaz no debe
    ofrecer un boton Deshacer que siempre va a fallar."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO moves_log (filename, source, destination, category, undoable) "
            "VALUES (?, ?, ?, ?, ?)",
            (filename, source, destination, category, 1 if undoable else 0),
        )
        return cur.lastrowid


def count_moves() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM moves_log").fetchone()
        return row["c"]


def _move_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["undoable"] = bool(d.get("undoable", 1)) and not d.get("undone_at")
    return d


def recent_moves(limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 500))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM moves_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_move_row_to_dict(r) for r in rows]


def get_move(move_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM moves_log WHERE id = ?", (move_id,)).fetchone()
        return dict(row) if row else None


def mark_move_undone(move_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE moves_log SET undone_at = datetime('now') WHERE id = ?", (move_id,)
        )


# ---- ajustes ----------------------------------------------------------------

def get_setting(key: str, default: str | None = None) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )


# ---- sugerencias de limpieza -----------------------------------------------

def add_cleanup_suggestion(path: str, reason: str, category: str = "cleanup") -> dict:
    """Registra un posible residuo sin borrarlo.

    La ruta se conserva para que la interfaz pueda pedir confirmacion sobre el
    elemento exacto. Si el usuario ya lo descarto, no se vuelve a abrir la
    misma sugerencia en cada barrido.
    """
    path = str(path)
    filename = path.replace("\\", "/").rsplit("/", 1)[-1]
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO cleanup_suggestions (path, filename, reason, category)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(path) DO UPDATE SET
                   filename = excluded.filename,
                   reason = excluded.reason,
                   category = excluded.category,
                   status = CASE
                       WHEN cleanup_suggestions.status = 'deleted' THEN 'deleted'
                       ELSE cleanup_suggestions.status
                   END""",
            (path, filename, reason, category),
        )
        row = conn.execute(
            "SELECT * FROM cleanup_suggestions WHERE path = ?", (path,)
        ).fetchone()
        return dict(row)


def list_cleanup_suggestions(status: str | None = "pending", limit: int = 100) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    with get_conn() as conn:
        if status is None:
            rows = conn.execute(
                "SELECT * FROM cleanup_suggestions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cleanup_suggestions WHERE status = ? "
                "ORDER BY id DESC LIMIT ?", (status, limit)
            ).fetchall()
        return [dict(row) for row in rows]


def get_cleanup_suggestion(suggestion_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM cleanup_suggestions WHERE id = ?", (int(suggestion_id),)
        ).fetchone()
        return dict(row) if row else None


def resolve_cleanup_suggestion(suggestion_id: int, status: str) -> dict | None:
    if status not in {"dismissed", "deleted", "missing"}:
        raise ValueError("estado de sugerencia no valido")
    with get_conn() as conn:
        conn.execute(
            "UPDATE cleanup_suggestions SET status = ?, resolved_at = datetime('now') "
            "WHERE id = ?",
            (status, int(suggestion_id)),
        )
        row = conn.execute(
            "SELECT * FROM cleanup_suggestions WHERE id = ?", (int(suggestion_id),)
        ).fetchone()
        return dict(row) if row else None


# ---- temas (topics) ----------------------------------------------------------

def _topic_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["keywords"] = [k.strip() for k in d["keywords"].split(",") if k.strip()]
    return d


def list_topics() -> list[dict]:
    global _topics_cache
    with _topics_cache_lock:
        if _topics_cache is not None:
            return [dict(t, keywords=list(t["keywords"])) for t in _topics_cache]
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM topics ORDER BY name").fetchall()
        result = [_topic_row_to_dict(r) for r in rows]
        with _topics_cache_lock:
            _topics_cache = result
        return [dict(t, keywords=list(t["keywords"])) for t in result]


def add_topic(name: str, destination: str, keywords: list[str], rename_pattern: str | None = None) -> dict:
    name = name.strip()
    destination = destination.strip().strip("/")
    keywords_str = ",".join(k.strip() for k in keywords if k.strip())
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO topics (name, destination, keywords, rename_pattern) VALUES (?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET destination = excluded.destination,
                                                    keywords = excluded.keywords,
                                                    rename_pattern = excluded.rename_pattern""",
                (name, destination, keywords_str, rename_pattern),
            )
            row = conn.execute("SELECT * FROM topics WHERE name = ?", (name,)).fetchone()
            return _topic_row_to_dict(row)
    finally:
        _invalidate_db_caches()
        try:
            from app.organizer import invalidate_scan_dirs_cache
            invalidate_scan_dirs_cache()
        except Exception:
            pass


def delete_topic(topic_id: int) -> None:
    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    finally:
        _invalidate_db_caches()
        try:
            from app.organizer import invalidate_scan_dirs_cache
            invalidate_scan_dirs_cache()
        except Exception:
            pass


# ---- maintenance rules -------------------------------------------------------

def list_maintenance_rules() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM maintenance_rules ORDER BY folder").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["directory_path"] = d["folder"]
            result.append(d)
        return result


def add_maintenance_rule(folder: str, max_age_days: int, active: int = 1) -> dict:
    folder = folder.strip()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO maintenance_rules (folder, max_age_days, active) VALUES (?, ?, ?)
               ON CONFLICT(folder) DO UPDATE SET max_age_days = excluded.max_age_days, active = excluded.active""",
            (folder, max_age_days, active),
        )
        row = conn.execute("SELECT * FROM maintenance_rules WHERE folder = ?", (folder,)).fetchone()
        d = dict(row)
        d["directory_path"] = d["folder"]
        return d


def delete_maintenance_rule(rule_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM maintenance_rules WHERE id = ?", (rule_id,))


# ---- watched folders ---------------------------------------------------------

def list_watched_folders() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM watched_folders ORDER BY folder_path").fetchall()
        return [dict(r) for r in rows]


def add_watched_folder(folder_path: str, active: int = 1) -> dict:
    folder_path = folder_path.strip()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO watched_folders (folder_path, active) VALUES (?, ?)
               ON CONFLICT(folder_path) DO UPDATE SET active = excluded.active""",
            (folder_path, active),
        )
        row = conn.execute("SELECT * FROM watched_folders WHERE folder_path = ?", (folder_path,)).fetchone()
        return dict(row)


def delete_watched_folder(folder_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watched_folders WHERE id = ?", (folder_id,))


# ---- statistics dashboard ----------------------------------------------------

def get_statistics() -> dict:
    with get_conn() as conn:
        total = conn.execute('SELECT COUNT(*) AS c FROM moves_log WHERE undone_at IS NULL').fetchone()['c']
        by_category = conn.execute('SELECT category, COUNT(*) AS c FROM moves_log WHERE undone_at IS NULL GROUP BY category ORDER BY c DESC').fetchall()
        by_day = conn.execute("SELECT date(moved_at) AS day, COUNT(*) AS c FROM moves_log WHERE undone_at IS NULL GROUP BY day ORDER BY day DESC LIMIT 30").fetchall()
        return {
            'total_organized': total,
            'by_category': [dict(r) for r in by_category],
            'by_day': [dict(r) for r in reversed(by_day)],
        }

