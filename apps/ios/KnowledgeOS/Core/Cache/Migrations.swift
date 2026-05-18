import Foundation

enum CacheMigrations {
    static let currentVersion: Int64 = 2

    /// Applies any pending migrations against the given database. Idempotent.
    static func apply(to db: SQLiteDatabase) throws {
        try db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );
        """)
        let rows = try db.query("SELECT version FROM schema_version WHERE id = 1") { row in
            row.int(0)
        }
        let current = rows.first ?? 0

        if current < 1 {
            try db.transaction { tx in
                try tx.execute("""
                    CREATE TABLE IF NOT EXISTS cached_objects (
                        id TEXT PRIMARY KEY NOT NULL,
                        kind TEXT NOT NULL,
                        payload_json BLOB NOT NULL,
                        fetched_at REAL NOT NULL
                    );
                """)
                // Spec column name is `object_id` (not `id`); we ship that here so v1
                // installs match the spec literally. v2 migrates older v1 installs that
                // used `id`.
                try tx.execute("""
                    CREATE TABLE IF NOT EXISTS cached_details (
                        object_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        payload_json BLOB NOT NULL,
                        fetched_at REAL NOT NULL,
                        PRIMARY KEY (object_id, kind)
                    );
                """)
                try tx.execute("""
                    CREATE TABLE IF NOT EXISTS cached_recent_objects (
                        page INTEGER PRIMARY KEY NOT NULL,
                        payload_json BLOB NOT NULL,
                        fetched_at REAL NOT NULL
                    );
                """)
                try tx.execute("""
                    CREATE TABLE IF NOT EXISTS cached_searches (
                        query TEXT PRIMARY KEY NOT NULL,
                        payload_json BLOB NOT NULL,
                        fetched_at REAL NOT NULL
                    );
                """)
                try tx.execute("""
                    CREATE TABLE IF NOT EXISTS pending_uploads (
                        id TEXT PRIMARY KEY NOT NULL,
                        kind TEXT NOT NULL,
                        payload BLOB NOT NULL,
                        retry_count INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT,
                        created_at REAL NOT NULL,
                        next_attempt_at REAL NOT NULL,
                        needs_attention INTEGER NOT NULL DEFAULT 0
                    );
                """)
                try tx.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pending_next_attempt
                    ON pending_uploads(next_attempt_at);
                """)
                if current == 0 {
                    try tx.execute(
                        "INSERT INTO schema_version (id, version) VALUES (1, 1)"
                    )
                } else {
                    try tx.execute(
                        "UPDATE schema_version SET version = 1 WHERE id = 1"
                    )
                }
            }
        }

        if current < 2 {
            // v2:
            //   - rename `cached_details.id` → `object_id` (spec literal alignment) if needed
            //   - add `pending_uploads.needs_attention` column for permanent (4xx) failures
            try db.transaction { tx in
                let cdCols = try Self.columnNames(of: "cached_details", in: tx)
                if cdCols.contains("id") && !cdCols.contains("object_id") {
                    try tx.execute("ALTER TABLE cached_details RENAME COLUMN id TO object_id;")
                }
                let puCols = try Self.columnNames(of: "pending_uploads", in: tx)
                if !puCols.contains("needs_attention") {
                    try tx.execute(
                        "ALTER TABLE pending_uploads ADD COLUMN needs_attention INTEGER NOT NULL DEFAULT 0;"
                    )
                }
                try tx.execute("UPDATE schema_version SET version = 2 WHERE id = 1")
            }
        }
    }

    private static func columnNames(of table: String, in tx: SQLiteDatabase.UnlockedDB) throws -> Set<String> {
        let rows = try tx.query(
            "PRAGMA table_info(\(table));"
        ) { row -> String? in
            row.text(1) // column 1 is `name` in PRAGMA table_info result.
        }
        return Set(rows.compactMap { $0 })
    }
}
