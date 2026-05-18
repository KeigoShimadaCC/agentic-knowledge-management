import Foundation

enum CacheMigrations {
    static let currentVersion: Int64 = 1

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
                try tx.execute("""
                    CREATE TABLE IF NOT EXISTS cached_details (
                        id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        payload_json BLOB NOT NULL,
                        fetched_at REAL NOT NULL,
                        PRIMARY KEY (id, kind)
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
                        next_attempt_at REAL NOT NULL
                    );
                """)
                try tx.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pending_next_attempt
                    ON pending_uploads(next_attempt_at);
                """)
                if current == 0 {
                    try tx.execute(
                        "INSERT INTO schema_version (id, version) VALUES (1, ?)",
                        bindings: [.integer(currentVersion)]
                    )
                } else {
                    try tx.execute(
                        "UPDATE schema_version SET version = ? WHERE id = 1",
                        bindings: [.integer(currentVersion)]
                    )
                }
            }
        }
    }
}
