import Foundation

enum PendingUploadKind: Equatable, Sendable {
    case quickNote
    case assetUpload(filename: String, mimeType: String, createSource: Bool)

    var raw: String {
        switch self {
        case .quickNote: return "quick_note"
        case .assetUpload: return "asset_upload"
        }
    }

    func encodedMetadata() throws -> Data {
        switch self {
        case .quickNote:
            return Data()
        case let .assetUpload(filename, mimeType, createSource):
            return try JSONCoding.encoder.encode([
                "filename": filename,
                "mimeType": mimeType,
                "createSource": String(createSource),
            ])
        }
    }

    static func decode(raw: String, metadata: Data) throws -> PendingUploadKind {
        switch raw {
        case "quick_note":
            return .quickNote
        case "asset_upload":
            let decoded = try JSONCoding.decoder.decode([String: String].self, from: metadata)
            guard
                let filename = decoded["filename"],
                let mimeType = decoded["mimeType"]
            else {
                throw NSError(
                    domain: "QueueStore",
                    code: 1,
                    userInfo: [NSLocalizedDescriptionKey: "missing asset metadata"]
                )
            }
            return .assetUpload(
                filename: filename,
                mimeType: mimeType,
                createSource: decoded["createSource"] == "true"
            )
        default:
            throw NSError(
                domain: "QueueStore",
                code: 2,
                userInfo: [NSLocalizedDescriptionKey: "unknown kind: \(raw)"]
            )
        }
    }
}

struct PendingUpload: Sendable, Equatable {
    let id: UUID
    let kind: PendingUploadKind
    /// Request-specific bytes. For `.quickNote` this is the JSON-encoded
    /// `PageCreateRequest`. For `.assetUpload` this is the raw file bytes.
    let payload: Data
    let metadata: Data
    let retryCount: Int
    let lastError: String?
    let createdAt: Date
    let nextAttemptAt: Date
}

protocol QueueStore: Sendable {
    func enqueue(_ item: PendingUpload) throws
    func pendingCount() throws -> Int
    func allPending() throws -> [PendingUpload]
    func nextDrainable(now: Date) throws -> [PendingUpload]
    func markSucceeded(id: UUID) throws
    func markFailed(id: UUID, error: String, now: Date) throws
    func remove(id: UUID) throws
    func observe() -> AsyncStream<Int>
}

extension QueueStore {
    /// Backoff: 60s · 2^retryCount, capped at 1h.
    static func nextAttempt(after now: Date, retryCount: Int) -> Date {
        let exponent = min(retryCount, 6) // 60 * 2^6 = 3840 ≈ 1h
        let delay = min(60.0 * pow(2.0, Double(exponent)), 3600.0)
        return now.addingTimeInterval(delay)
    }

    static var maxRetries: Int { 10 }
}

/// SQLite-backed implementation.
final class SystemQueueStore: QueueStore, @unchecked Sendable {
    private let db: SQLiteDatabase
    private let lock = NSLock()
    private var observers: [UUID: AsyncStream<Int>.Continuation] = [:]

    init(db: SQLiteDatabase) throws {
        self.db = db
        try CacheMigrations.apply(to: db)
    }

    convenience init() throws {
        try self.init(db: try SQLiteDatabase())
    }

    func enqueue(_ item: PendingUpload) throws {
        try db.execute(
            """
            INSERT INTO pending_uploads
                (id, kind, payload, retry_count, last_error, created_at, next_attempt_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind = excluded.kind,
                payload = excluded.payload,
                retry_count = excluded.retry_count,
                last_error = excluded.last_error,
                next_attempt_at = excluded.next_attempt_at;
            """,
            bindings: [
                .text(item.id.uuidString),
                .text(item.kind.raw),
                .blob(combine(payload: item.payload, metadata: item.metadata)),
                .integer(Int64(item.retryCount)),
                item.lastError.map { .text($0) } ?? .null,
                .real(item.createdAt.timeIntervalSince1970),
                .real(item.nextAttemptAt.timeIntervalSince1970),
            ]
        )
        notify()
    }

    func pendingCount() throws -> Int {
        let rows = try db.query("SELECT COUNT(*) FROM pending_uploads") { row in
            Int(row.int(0))
        }
        return rows.first ?? 0
    }

    func allPending() throws -> [PendingUpload] {
        try db.query(
            "SELECT id, kind, payload, retry_count, last_error, created_at, next_attempt_at FROM pending_uploads ORDER BY created_at ASC",
            rowDecoder: decodeRow
        ).compactMap { $0 }
    }

    func nextDrainable(now: Date) throws -> [PendingUpload] {
        try db.query(
            """
            SELECT id, kind, payload, retry_count, last_error, created_at, next_attempt_at
            FROM pending_uploads
            WHERE next_attempt_at <= ?
            ORDER BY next_attempt_at ASC
            LIMIT 25
            """,
            bindings: [.real(now.timeIntervalSince1970)],
            rowDecoder: decodeRow
        ).compactMap { $0 }
    }

    func markSucceeded(id: UUID) throws {
        try remove(id: id)
    }

    func markFailed(id: UUID, error: String, now: Date) throws {
        let rows = try db.query(
            "SELECT retry_count FROM pending_uploads WHERE id = ?",
            bindings: [.text(id.uuidString)]
        ) { row in
            Int(row.int(0))
        }
        let currentRetries = rows.first ?? 0
        let nextRetries = currentRetries + 1
        if nextRetries > Self.maxRetries {
            // Park: don't drop, but push the next attempt 24h out so it surfaces but
            // doesn't keep churning.
            try db.execute(
                "UPDATE pending_uploads SET retry_count = ?, last_error = ?, next_attempt_at = ? WHERE id = ?",
                bindings: [
                    .integer(Int64(nextRetries)),
                    .text(error),
                    .real(now.addingTimeInterval(24 * 3600).timeIntervalSince1970),
                    .text(id.uuidString),
                ]
            )
        } else {
            let next = Self.nextAttempt(after: now, retryCount: nextRetries)
            try db.execute(
                "UPDATE pending_uploads SET retry_count = ?, last_error = ?, next_attempt_at = ? WHERE id = ?",
                bindings: [
                    .integer(Int64(nextRetries)),
                    .text(error),
                    .real(next.timeIntervalSince1970),
                    .text(id.uuidString),
                ]
            )
        }
        notify()
    }

    func remove(id: UUID) throws {
        try db.execute(
            "DELETE FROM pending_uploads WHERE id = ?",
            bindings: [.text(id.uuidString)]
        )
        notify()
    }

    func observe() -> AsyncStream<Int> {
        AsyncStream { continuation in
            let key = UUID()
            lock.lock()
            observers[key] = continuation
            lock.unlock()
            // Emit the current count immediately.
            if let count = try? pendingCount() {
                continuation.yield(count)
            }
            continuation.onTermination = { [weak self] _ in
                self?.lock.lock()
                self?.observers.removeValue(forKey: key)
                self?.lock.unlock()
            }
        }
    }

    private func notify() {
        guard let count = try? pendingCount() else { return }
        lock.lock()
        let snapshot = Array(observers.values)
        lock.unlock()
        for cont in snapshot { cont.yield(count) }
    }

    // MARK: - encode / decode helpers

    /// We pack (payload, metadata) into a single sqlite blob so the schema stays
    /// fixed at 7 columns. Layout: 4-byte big-endian payload length || payload || metadata.
    private func combine(payload: Data, metadata: Data) -> Data {
        var out = Data()
        var len = UInt32(payload.count).bigEndian
        out.append(Data(bytes: &len, count: 4))
        out.append(payload)
        out.append(metadata)
        return out
    }

    private func split(_ blob: Data) -> (payload: Data, metadata: Data) {
        guard blob.count >= 4 else { return (blob, Data()) }
        let header = blob.prefix(4)
        let len = header.withUnsafeBytes { raw -> Int in
            let value = raw.load(as: UInt32.self).bigEndian
            return Int(value)
        }
        let payload = blob.dropFirst(4).prefix(len)
        let metadata = blob.dropFirst(4 + len)
        return (Data(payload), Data(metadata))
    }

    private func decodeRow(_ row: SQLiteDatabase.Row) -> PendingUpload? {
        guard
            let idStr = row.text(0),
            let id = UUID(uuidString: idStr),
            let kindStr = row.text(1),
            let blob = row.blob(2)
        else { return nil }
        let (payload, metadata) = split(blob)
        let kind: PendingUploadKind
        do {
            kind = try PendingUploadKind.decode(raw: kindStr, metadata: metadata)
        } catch {
            return nil
        }
        return PendingUpload(
            id: id,
            kind: kind,
            payload: payload,
            metadata: metadata,
            retryCount: Int(row.int(3)),
            lastError: row.text(4),
            createdAt: Date(timeIntervalSince1970: row.double(5)),
            nextAttemptAt: Date(timeIntervalSince1970: row.double(6))
        )
    }
}

/// Process-lifetime fallback when on-disk SQLite cannot be opened. Used by
/// `AppDependencies` as a last resort; tests prefer it for simplicity.
final class InMemoryQueueStore: QueueStore, @unchecked Sendable {
    private let lock = NSLock()
    private var items: [UUID: PendingUpload] = [:]
    private var observers: [UUID: AsyncStream<Int>.Continuation] = [:]

    init() {}

    func enqueue(_ item: PendingUpload) throws {
        lock.lock(); items[item.id] = item; lock.unlock()
        notify()
    }

    func pendingCount() throws -> Int {
        lock.lock(); defer { lock.unlock() }
        return items.count
    }

    func allPending() throws -> [PendingUpload] {
        lock.lock(); defer { lock.unlock() }
        return Array(items.values).sorted { $0.createdAt < $1.createdAt }
    }

    func nextDrainable(now: Date) throws -> [PendingUpload] {
        lock.lock(); defer { lock.unlock() }
        return items.values
            .filter { $0.nextAttemptAt <= now }
            .sorted { $0.nextAttemptAt < $1.nextAttemptAt }
    }

    func markSucceeded(id: UUID) throws {
        lock.lock(); items.removeValue(forKey: id); lock.unlock()
        notify()
    }

    func markFailed(id: UUID, error: String, now: Date) throws {
        lock.lock()
        if let existing = items[id] {
            let nextRetries = existing.retryCount + 1
            let next = Self.nextAttempt(after: now, retryCount: nextRetries)
            items[id] = PendingUpload(
                id: existing.id,
                kind: existing.kind,
                payload: existing.payload,
                metadata: existing.metadata,
                retryCount: nextRetries,
                lastError: error,
                createdAt: existing.createdAt,
                nextAttemptAt: nextRetries > Self.maxRetries
                    ? now.addingTimeInterval(24 * 3600)
                    : next
            )
        }
        lock.unlock()
        notify()
    }

    func remove(id: UUID) throws {
        lock.lock(); items.removeValue(forKey: id); lock.unlock()
        notify()
    }

    func observe() -> AsyncStream<Int> {
        AsyncStream { continuation in
            let key = UUID()
            lock.lock(); observers[key] = continuation; lock.unlock()
            continuation.yield((try? pendingCount()) ?? 0)
            continuation.onTermination = { [weak self] _ in
                self?.lock.lock()
                self?.observers.removeValue(forKey: key)
                self?.lock.unlock()
            }
        }
    }

    private func notify() {
        let count = (try? pendingCount()) ?? 0
        lock.lock()
        let snapshot = Array(observers.values)
        lock.unlock()
        for cont in snapshot { cont.yield(count) }
    }
}
