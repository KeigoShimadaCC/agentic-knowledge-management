import Foundation
import SQLite3

enum SQLiteError: Error, Equatable {
    case openFailed(Int32, String)
    case prepareFailed(Int32, String)
    case stepFailed(Int32, String)
    case bindFailed(Int32, String)
    case unexpectedColumnType(String)
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

/// Minimal thread-safe sqlite3 wrapper. Single shared connection serialized via a
/// private queue. All reads and writes go through `execute(_:)` / `query(_:rowDecoder:)`.
final class SQLiteDatabase: @unchecked Sendable {
    enum Value {
        case null
        case integer(Int64)
        case real(Double)
        case text(String)
        case blob(Data)
    }

    final class Row {
        private let handle: OpaquePointer
        init(_ handle: OpaquePointer) { self.handle = handle }

        func int(_ idx: Int32) -> Int64 { sqlite3_column_int64(handle, idx) }

        func text(_ idx: Int32) -> String? {
            guard let cstr = sqlite3_column_text(handle, idx) else { return nil }
            return String(cString: cstr)
        }

        func blob(_ idx: Int32) -> Data? {
            guard let bytes = sqlite3_column_blob(handle, idx) else { return nil }
            let count = Int(sqlite3_column_bytes(handle, idx))
            return Data(bytes: bytes, count: count)
        }

        func double(_ idx: Int32) -> Double { sqlite3_column_double(handle, idx) }
    }

    private var handle: OpaquePointer?
    private let queue = DispatchQueue(label: "com.knowledgeos.sqlite")
    let path: String

    /// Path under `Library/Caches/knowledgeos.sqlite` by default. Pass an explicit path
    /// (e.g. an `NSTemporaryDirectory()` file) for tests.
    init(path: String? = nil) throws {
        let resolved = try path ?? Self.defaultPath()
        self.path = resolved
        let flags = SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE | SQLITE_OPEN_FULLMUTEX
        let rc = sqlite3_open_v2(resolved, &handle, flags, nil)
        guard rc == SQLITE_OK, let handle else {
            let msg = handle.flatMap { String(cString: sqlite3_errmsg($0)) } ?? "unknown"
            sqlite3_close(handle)
            throw SQLiteError.openFailed(rc, msg)
        }
        // Recommended pragmas for concurrent access and durability.
        try perform { sqlite3_exec(handle, "PRAGMA journal_mode=WAL;", nil, nil, nil) }
        try perform { sqlite3_exec(handle, "PRAGMA foreign_keys=ON;", nil, nil, nil) }
    }

    deinit {
        if let handle { sqlite3_close(handle) }
    }

    /// Execute a write statement.
    func execute(_ sql: String, bindings: [Value] = []) throws {
        try queue.sync { try executeUnlocked(sql, bindings: bindings) }
    }

    /// Run a read query; map each row through `rowDecoder`.
    func query<T>(_ sql: String, bindings: [Value] = [], rowDecoder: (Row) -> T) throws -> [T] {
        try queue.sync { try queryUnlocked(sql, bindings: bindings, rowDecoder: rowDecoder) }
    }

    /// Run `body` inside a transaction. Rolls back on throw. `body` MUST use the
    /// `unlocked` API on the database it receives — re-entering the locked variants
    /// would deadlock the dispatch queue.
    func transaction(_ body: (UnlockedDB) throws -> Void) throws {
        try queue.sync {
            try perform { sqlite3_exec(handle, "BEGIN IMMEDIATE", nil, nil, nil) }
            do {
                try body(UnlockedDB(parent: self))
                try perform { sqlite3_exec(handle, "COMMIT", nil, nil, nil) }
            } catch {
                _ = sqlite3_exec(handle, "ROLLBACK", nil, nil, nil)
                throw error
            }
        }
    }

    /// Pass-through into the locked statement runner — used by `UnlockedDB`.
    fileprivate func executeUnlocked(_ sql: String, bindings: [Value]) throws {
        guard let stmt = try prepare(sql: sql) else { return }
        defer { sqlite3_finalize(stmt) }
        try bind(stmt: stmt, bindings: bindings)
        let rc = sqlite3_step(stmt)
        guard rc == SQLITE_DONE else { throw SQLiteError.stepFailed(rc, lastErrorMessage()) }
    }

    fileprivate func queryUnlocked<T>(_ sql: String, bindings: [Value], rowDecoder: (Row) -> T) throws -> [T] {
        guard let stmt = try prepare(sql: sql) else { return [] }
        defer { sqlite3_finalize(stmt) }
        try bind(stmt: stmt, bindings: bindings)
        var out: [T] = []
        while true {
            let rc = sqlite3_step(stmt)
            if rc == SQLITE_ROW {
                out.append(rowDecoder(Row(stmt)))
            } else if rc == SQLITE_DONE {
                break
            } else {
                throw SQLiteError.stepFailed(rc, lastErrorMessage())
            }
        }
        return out
    }

    /// Handed to transaction bodies. Forwards to the parent database without re-acquiring
    /// the dispatch queue, since the transaction is already inside `queue.sync`.
    struct UnlockedDB {
        fileprivate let parent: SQLiteDatabase
        func execute(_ sql: String, bindings: [Value] = []) throws {
            try parent.executeUnlocked(sql, bindings: bindings)
        }
        func query<T>(_ sql: String, bindings: [Value] = [], rowDecoder: (Row) -> T) throws -> [T] {
            try parent.queryUnlocked(sql, bindings: bindings, rowDecoder: rowDecoder)
        }
    }

    // MARK: - Internals

    private func prepare(sql: String) throws -> OpaquePointer? {
        var stmt: OpaquePointer?
        let rc = sqlite3_prepare_v2(handle, sql, -1, &stmt, nil)
        guard rc == SQLITE_OK else { throw SQLiteError.prepareFailed(rc, lastErrorMessage()) }
        return stmt
    }

    private func bind(stmt: OpaquePointer?, bindings: [Value]) throws {
        for (idx, value) in bindings.enumerated() {
            let pos = Int32(idx + 1)
            let rc: Int32
            switch value {
            case .null:
                rc = sqlite3_bind_null(stmt, pos)
            case let .integer(i):
                rc = sqlite3_bind_int64(stmt, pos, i)
            case let .real(d):
                rc = sqlite3_bind_double(stmt, pos, d)
            case let .text(s):
                rc = sqlite3_bind_text(stmt, pos, s, -1, SQLITE_TRANSIENT)
            case let .blob(data):
                rc = data.withUnsafeBytes { raw in
                    sqlite3_bind_blob(stmt, pos, raw.baseAddress, Int32(data.count), SQLITE_TRANSIENT)
                }
            }
            guard rc == SQLITE_OK else { throw SQLiteError.bindFailed(rc, lastErrorMessage()) }
        }
    }

    private func perform(_ block: () -> Int32) throws {
        let rc = block()
        guard rc == SQLITE_OK else { throw SQLiteError.stepFailed(rc, lastErrorMessage()) }
    }

    private func lastErrorMessage() -> String {
        handle.flatMap { String(cString: sqlite3_errmsg($0)) } ?? "unknown"
    }

    private static func defaultPath() throws -> String {
        let fm = FileManager.default
        let base = try fm.url(for: .cachesDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let dir = base.appendingPathComponent("knowledgeos", isDirectory: true)
        try fm.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("knowledgeos.sqlite").path
    }
}
