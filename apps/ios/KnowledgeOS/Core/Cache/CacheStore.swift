import Foundation

struct CachedEntry<T> {
    let value: T
    let fetchedAt: Date

    /// `true` if the entry is older than the given TTL.
    func isStale(now: Date = Date(), ttl: TimeInterval) -> Bool {
        now.timeIntervalSince(fetchedAt) > ttl
    }
}

protocol CacheStore: Sendable {
    func cachedObject(id: UUID) -> CachedEntry<ObjectDTO>?
    func saveObject(_ object: ObjectDTO) throws

    func cachedPage(id: UUID) -> CachedEntry<PageDTO>?
    func savePage(id: UUID, page: PageDTO) throws

    func cachedSource(id: UUID) -> CachedEntry<SourceDTO>?
    func saveSource(id: UUID, source: SourceDTO) throws

    func cachedChat(id: UUID) -> CachedEntry<ChatDTO>?
    func saveChat(id: UUID, chat: ChatDTO) throws

    func cachedProject(id: UUID) -> CachedEntry<ProjectDTO>?
    func saveProject(id: UUID, project: ProjectDTO) throws

    func cachedRecentObjects(page: Int) -> CachedEntry<PaginatedResponseDTO<ObjectDTO>>?
    func saveRecentObjects(page: Int, response: PaginatedResponseDTO<ObjectDTO>) throws

    func cachedSearch(query: String) -> CachedEntry<HybridSearchResponseDTO>?
    func saveSearch(query: String, response: HybridSearchResponseDTO) throws

    func clearAll() throws
}

/// Production implementation backed by SQLite.
final class SystemCacheStore: CacheStore, @unchecked Sendable {
    private let db: SQLiteDatabase

    init(db: SQLiteDatabase) throws {
        self.db = db
        try CacheMigrations.apply(to: db)
    }

    convenience init() throws {
        try self.init(db: try SQLiteDatabase())
    }

    // MARK: - Objects (used by ObjectDetail dispatcher)

    func cachedObject(id: UUID) -> CachedEntry<ObjectDTO>? {
        readDetail(id: id, kind: "object")
    }

    func saveObject(_ object: ObjectDTO) throws {
        try writeDetail(id: object.id, kind: "object", payload: object)
        // Also store in cached_objects keyed by id for quick lookups by kind dispatching.
        let data = try JSONCoding.encoder.encode(object)
        try db.execute(
            """
            INSERT INTO cached_objects (id, kind, payload_json, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind = excluded.kind,
                payload_json = excluded.payload_json,
                fetched_at = excluded.fetched_at;
            """,
            bindings: [
                .text(object.id.uuidString),
                .text(object.kind),
                .blob(data),
                .real(Date().timeIntervalSince1970),
            ]
        )
    }

    // MARK: - Typed details

    func cachedPage(id: UUID) -> CachedEntry<PageDTO>? { readDetail(id: id, kind: "page") }
    func savePage(id: UUID, page: PageDTO) throws { try writeDetail(id: id, kind: "page", payload: page) }

    func cachedSource(id: UUID) -> CachedEntry<SourceDTO>? { readDetail(id: id, kind: "source") }
    func saveSource(id: UUID, source: SourceDTO) throws { try writeDetail(id: id, kind: "source", payload: source) }

    func cachedChat(id: UUID) -> CachedEntry<ChatDTO>? { readDetail(id: id, kind: "chat") }
    func saveChat(id: UUID, chat: ChatDTO) throws { try writeDetail(id: id, kind: "chat", payload: chat) }

    func cachedProject(id: UUID) -> CachedEntry<ProjectDTO>? { readDetail(id: id, kind: "project") }
    func saveProject(id: UUID, project: ProjectDTO) throws { try writeDetail(id: id, kind: "project", payload: project) }

    // MARK: - Lists

    func cachedRecentObjects(page: Int) -> CachedEntry<PaginatedResponseDTO<ObjectDTO>>? {
        let rows = (try? db.query(
            "SELECT payload_json, fetched_at FROM cached_recent_objects WHERE page = ?",
            bindings: [.integer(Int64(page))]
        ) { row -> (Data, Double)? in
            guard let data = row.blob(0) else { return nil }
            return (data, row.double(1))
        }) ?? []
        guard let tuple = rows.compactMap({ $0 }).first else { return nil }
        guard let decoded = try? JSONCoding.decoder.decode(PaginatedResponseDTO<ObjectDTO>.self, from: tuple.0) else { return nil }
        return CachedEntry(value: decoded, fetchedAt: Date(timeIntervalSince1970: tuple.1))
    }

    func saveRecentObjects(page: Int, response: PaginatedResponseDTO<ObjectDTO>) throws {
        let data = try JSONCoding.encoder.encode(response)
        try db.execute(
            """
            INSERT INTO cached_recent_objects (page, payload_json, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(page) DO UPDATE SET
                payload_json = excluded.payload_json,
                fetched_at = excluded.fetched_at;
            """,
            bindings: [
                .integer(Int64(page)),
                .blob(data),
                .real(Date().timeIntervalSince1970),
            ]
        )
    }

    func cachedSearch(query: String) -> CachedEntry<HybridSearchResponseDTO>? {
        let key = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let rows = (try? db.query(
            "SELECT payload_json, fetched_at FROM cached_searches WHERE query = ?",
            bindings: [.text(key)]
        ) { row -> (Data, Double)? in
            guard let data = row.blob(0) else { return nil }
            return (data, row.double(1))
        }) ?? []
        guard let tuple = rows.compactMap({ $0 }).first else { return nil }
        guard let decoded = try? JSONCoding.decoder.decode(HybridSearchResponseDTO.self, from: tuple.0) else { return nil }
        return CachedEntry(value: decoded, fetchedAt: Date(timeIntervalSince1970: tuple.1))
    }

    func saveSearch(query: String, response: HybridSearchResponseDTO) throws {
        let key = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let data = try JSONCoding.encoder.encode(response)
        try db.execute(
            """
            INSERT INTO cached_searches (query, payload_json, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(query) DO UPDATE SET
                payload_json = excluded.payload_json,
                fetched_at = excluded.fetched_at;
            """,
            bindings: [
                .text(key),
                .blob(data),
                .real(Date().timeIntervalSince1970),
            ]
        )
    }

    func clearAll() throws {
        try db.execute("DELETE FROM cached_objects")
        try db.execute("DELETE FROM cached_details")
        try db.execute("DELETE FROM cached_recent_objects")
        try db.execute("DELETE FROM cached_searches")
    }

    // MARK: - Internal helpers

    private func readDetail<T: Decodable>(id: UUID, kind: String) -> CachedEntry<T>? {
        let rows = (try? db.query(
            "SELECT payload_json, fetched_at FROM cached_details WHERE object_id = ? AND kind = ?",
            bindings: [.text(id.uuidString), .text(kind)]
        ) { row -> (Data, Double)? in
            guard let data = row.blob(0) else { return nil }
            return (data, row.double(1))
        }) ?? []
        guard let tuple = rows.compactMap({ $0 }).first else { return nil }
        guard let decoded = try? JSONCoding.decoder.decode(T.self, from: tuple.0) else { return nil }
        return CachedEntry(value: decoded, fetchedAt: Date(timeIntervalSince1970: tuple.1))
    }

    private func writeDetail<T: Encodable>(id: UUID, kind: String, payload: T) throws {
        let data = try JSONCoding.encoder.encode(payload)
        try db.execute(
            """
            INSERT INTO cached_details (object_id, kind, payload_json, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(object_id, kind) DO UPDATE SET
                payload_json = excluded.payload_json,
                fetched_at = excluded.fetched_at;
            """,
            bindings: [
                .text(id.uuidString),
                .text(kind),
                .blob(data),
                .real(Date().timeIntervalSince1970),
            ]
        )
    }
}

/// In-memory implementation used by tests and previews.
final class InMemoryCacheStore: CacheStore, @unchecked Sendable {
    private let lock = NSLock()
    private var objects: [UUID: CachedEntry<ObjectDTO>] = [:]
    private var pages: [UUID: CachedEntry<PageDTO>] = [:]
    private var sources: [UUID: CachedEntry<SourceDTO>] = [:]
    private var chats: [UUID: CachedEntry<ChatDTO>] = [:]
    private var projects: [UUID: CachedEntry<ProjectDTO>] = [:]
    private var recents: [Int: CachedEntry<PaginatedResponseDTO<ObjectDTO>>] = [:]
    private var searches: [String: CachedEntry<HybridSearchResponseDTO>] = [:]

    init() {}

    func cachedObject(id: UUID) -> CachedEntry<ObjectDTO>? {
        lock.lock(); defer { lock.unlock() }
        return objects[id]
    }

    func saveObject(_ object: ObjectDTO) throws {
        lock.lock(); defer { lock.unlock() }
        objects[object.id] = CachedEntry(value: object, fetchedAt: Date())
    }

    func cachedPage(id: UUID) -> CachedEntry<PageDTO>? {
        lock.lock(); defer { lock.unlock() }
        return pages[id]
    }
    func savePage(id: UUID, page: PageDTO) throws {
        lock.lock(); defer { lock.unlock() }
        pages[id] = CachedEntry(value: page, fetchedAt: Date())
    }

    func cachedSource(id: UUID) -> CachedEntry<SourceDTO>? {
        lock.lock(); defer { lock.unlock() }
        return sources[id]
    }
    func saveSource(id: UUID, source: SourceDTO) throws {
        lock.lock(); defer { lock.unlock() }
        sources[id] = CachedEntry(value: source, fetchedAt: Date())
    }

    func cachedChat(id: UUID) -> CachedEntry<ChatDTO>? {
        lock.lock(); defer { lock.unlock() }
        return chats[id]
    }
    func saveChat(id: UUID, chat: ChatDTO) throws {
        lock.lock(); defer { lock.unlock() }
        chats[id] = CachedEntry(value: chat, fetchedAt: Date())
    }

    func cachedProject(id: UUID) -> CachedEntry<ProjectDTO>? {
        lock.lock(); defer { lock.unlock() }
        return projects[id]
    }
    func saveProject(id: UUID, project: ProjectDTO) throws {
        lock.lock(); defer { lock.unlock() }
        projects[id] = CachedEntry(value: project, fetchedAt: Date())
    }

    func cachedRecentObjects(page: Int) -> CachedEntry<PaginatedResponseDTO<ObjectDTO>>? {
        lock.lock(); defer { lock.unlock() }
        return recents[page]
    }
    func saveRecentObjects(page: Int, response: PaginatedResponseDTO<ObjectDTO>) throws {
        lock.lock(); defer { lock.unlock() }
        recents[page] = CachedEntry(value: response, fetchedAt: Date())
    }

    func cachedSearch(query: String) -> CachedEntry<HybridSearchResponseDTO>? {
        lock.lock(); defer { lock.unlock() }
        return searches[normalize(query)]
    }
    func saveSearch(query: String, response: HybridSearchResponseDTO) throws {
        lock.lock(); defer { lock.unlock() }
        searches[normalize(query)] = CachedEntry(value: response, fetchedAt: Date())
    }

    func clearAll() throws {
        lock.lock(); defer { lock.unlock() }
        objects.removeAll(); pages.removeAll(); sources.removeAll()
        chats.removeAll(); projects.removeAll()
        recents.removeAll(); searches.removeAll()
    }

    private func normalize(_ query: String) -> String {
        query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    }
}
