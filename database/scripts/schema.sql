-- Esquema SQLite de Martix

-- Varias reglas pueden compartir extension: es justo el sentido de las
-- condiciones ("pdf que contiene factura" vs "pdf que contiene contrato").
-- El indice es NO unico a proposito; 'priority' fija en que orden se evaluan
-- (menor = se comprueba antes).
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    extension TEXT NOT NULL,       -- sin punto, minusculas, ej. "pdf"
    destination TEXT NOT NULL,     -- ruta relativa a la carpeta personal, ej. "Documents/Facturas"
    rename_pattern TEXT,
    conditions TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rules_extension ON rules(extension);

CREATE TABLE IF NOT EXISTS moves_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    category TEXT NOT NULL,
    moved_at TEXT NOT NULL DEFAULT (datetime('now')),
    undone_at TEXT,                -- fecha en que se deshizo el movimiento, si se deshizo
    -- 0 para eventos que no se pueden revertir (un desempaquetado, un borrado
    -- por mantenimiento): la interfaz no debe ofrecer "Deshacer" ahi.
    undoable INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_moves_log_moved_at ON moves_log(moved_at);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Temas definidos por el usuario: cualquier cosa (banco, gimnasio, una app
-- concreta...), no solo la universidad. Si el nombre/contenido de un
-- documento contiene alguna de sus palabras clave, se archiva en 'destination'.
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,      -- ej. "Banco", "Gimnasio", "Netflix"
    destination TEXT NOT NULL,      -- ruta relativa a la carpeta personal, ej. "Documents/Banco"
    keywords TEXT NOT NULL,         -- palabras clave separadas por comas
    rename_pattern TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watched_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Possible cleanup candidates are suggestions, never silent deletions.  The
-- path is kept so the user can review the exact item before sending it to the
-- native trash; it is not a licence to delete anything permanently.
CREATE TABLE IF NOT EXISTS cleanup_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    reason TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'cleanup',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_cleanup_suggestions_status
    ON cleanup_suggestions(status, created_at);
