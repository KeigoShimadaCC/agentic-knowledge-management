import XCTest
@testable import KnowledgeOS

@MainActor
final class CacheMigrationTests: XCTestCase {
    func testFreshDBLandsOnV2Schema() throws {
        let path = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-cache-mig-fresh-\(UUID()).sqlite").path
        defer { try? FileManager.default.removeItem(atPath: path) }

        let db = try SQLiteDatabase(path: path)
        try CacheMigrations.apply(to: db)

        let version = try db.query("SELECT version FROM schema_version") { row in row.int(0) }.first ?? 0
        XCTAssertEqual(version, CacheMigrations.currentVersion)

        // cached_details has object_id, pending_uploads has needs_attention.
        let cd = try db.query("PRAGMA table_info(cached_details)") { row in row.text(1) }
        XCTAssertTrue(cd.compactMap { $0 }.contains("object_id"))
        let pu = try db.query("PRAGMA table_info(pending_uploads)") { row in row.text(1) }
        XCTAssertTrue(pu.compactMap { $0 }.contains("needs_attention"))
    }

    func testV1ToV2MigrationRenamesAndAdds() throws {
        let path = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-cache-mig-v1-\(UUID()).sqlite").path
        defer { try? FileManager.default.removeItem(atPath: path) }

        // Hand-build a v1 schema (with the old `id` column on cached_details and no
        // needs_attention column).
        do {
            let db = try SQLiteDatabase(path: path)
            try db.execute("""
                CREATE TABLE schema_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL
                );
            """)
            try db.execute("""
                CREATE TABLE cached_details (
                    id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json BLOB NOT NULL,
                    fetched_at REAL NOT NULL,
                    PRIMARY KEY (id, kind)
                );
            """)
            try db.execute("""
                CREATE TABLE pending_uploads (
                    id TEXT PRIMARY KEY NOT NULL,
                    kind TEXT NOT NULL,
                    payload BLOB NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    next_attempt_at REAL NOT NULL
                );
            """)
            try db.execute(
                "INSERT INTO cached_details (id, kind, payload_json, fetched_at) VALUES (?, ?, ?, ?)",
                bindings: [
                    .text(UUID().uuidString),
                    .text("page"),
                    .blob(Data("{}".utf8)),
                    .real(0),
                ]
            )
            try db.execute("INSERT INTO schema_version (id, version) VALUES (1, 1)")
        }

        // Re-open and apply migrations — should rename + add column without losing data.
        let db2 = try SQLiteDatabase(path: path)
        try CacheMigrations.apply(to: db2)

        let cd = try db2.query("PRAGMA table_info(cached_details)") { row in row.text(1) }
        XCTAssertTrue(cd.compactMap { $0 }.contains("object_id"))
        XCTAssertFalse(cd.compactMap { $0 }.contains("id"), "v1 `id` should be renamed away")

        let pu = try db2.query("PRAGMA table_info(pending_uploads)") { row in row.text(1) }
        XCTAssertTrue(pu.compactMap { $0 }.contains("needs_attention"))

        let count = try db2.query("SELECT COUNT(*) FROM cached_details") { row in Int(row.int(0)) }
        XCTAssertEqual(count.first, 1, "existing rows must survive the column rename")

        let version = try db2.query("SELECT version FROM schema_version") { row in row.int(0) }.first ?? 0
        XCTAssertEqual(version, 2)
    }
}
