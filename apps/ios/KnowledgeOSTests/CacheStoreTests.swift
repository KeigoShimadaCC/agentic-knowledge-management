import XCTest
@testable import KnowledgeOS

@MainActor
final class CacheStoreTests: XCTestCase {
    private var tempPath: String!

    override func setUpWithError() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-phone-05-cache-\(UUID().uuidString).sqlite")
        tempPath = url.path
    }

    override func tearDownWithError() throws {
        if let tempPath { try? FileManager.default.removeItem(atPath: tempPath) }
    }

    func testFreshDBMigratesAndAcceptsObjects() throws {
        let db = try SQLiteDatabase(path: tempPath)
        let store = try SystemCacheStore(db: db)

        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        try store.saveObject(object)

        let hit = store.cachedObject(id: object.id)
        XCTAssertNotNil(hit)
        XCTAssertEqual(hit?.value.title, object.title)
    }

    func testDetailRoundtripForEachKind() throws {
        let db = try SQLiteDatabase(path: tempPath)
        let store = try SystemCacheStore(db: db)
        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        let page = try FixtureLoader.decode(PageDTO.self, named: "page")

        try store.savePage(id: object.id, page: page)
        XCTAssertEqual(store.cachedPage(id: object.id)?.value.contentText, "Hello")

        // Detail layer separates payload by kind even with same id.
        try store.saveObject(object)
        XCTAssertNotNil(store.cachedObject(id: object.id))
        XCTAssertNotNil(store.cachedPage(id: object.id))
    }

    func testRecentObjectsByPage() throws {
        let db = try SQLiteDatabase(path: tempPath)
        let store = try SystemCacheStore(db: db)
        let response = try FixtureLoader.decode(PaginatedResponseDTO<ObjectDTO>.self, named: "paginated_objects")

        try store.saveRecentObjects(page: 1, response: response)
        XCTAssertEqual(store.cachedRecentObjects(page: 1)?.value.items.count, response.items.count)
        XCTAssertNil(store.cachedRecentObjects(page: 2))
    }

    func testSearchKeyNormalizedToLowercaseTrimmed() throws {
        let db = try SQLiteDatabase(path: tempPath)
        let store = try SystemCacheStore(db: db)
        let search = try FixtureLoader.decode(HybridSearchResponseDTO.self, named: "hybrid_search")

        try store.saveSearch(query: "  Demo  ", response: search)
        XCTAssertNotNil(store.cachedSearch(query: "demo"))
        XCTAssertNotNil(store.cachedSearch(query: "DEMO"))
    }

    func testIsStaleHonorsTTL() {
        let entry = CachedEntry(value: 42, fetchedAt: Date().addingTimeInterval(-120))
        XCTAssertTrue(entry.isStale(ttl: 60))
        XCTAssertFalse(entry.isStale(ttl: 600))
    }

    func testClearAllEmptiesEveryTable() throws {
        let db = try SQLiteDatabase(path: tempPath)
        let store = try SystemCacheStore(db: db)
        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        let page = try FixtureLoader.decode(PageDTO.self, named: "page")
        try store.saveObject(object)
        try store.savePage(id: object.id, page: page)
        try store.clearAll()
        XCTAssertNil(store.cachedObject(id: object.id))
        XCTAssertNil(store.cachedPage(id: object.id))
    }

    func testReopenSameFileRetainsData() throws {
        // Persistence across "relaunch": open, write, drop, reopen, read.
        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        do {
            let db = try SQLiteDatabase(path: tempPath)
            let store = try SystemCacheStore(db: db)
            try store.saveObject(object)
        }
        let db2 = try SQLiteDatabase(path: tempPath)
        let store2 = try SystemCacheStore(db: db2)
        XCTAssertEqual(store2.cachedObject(id: object.id)?.value.id, object.id)
    }
}
