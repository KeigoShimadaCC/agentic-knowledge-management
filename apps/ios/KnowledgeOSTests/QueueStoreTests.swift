import XCTest
@testable import KnowledgeOS

@MainActor
final class QueueStoreTests: XCTestCase {
    private var tempPath: String!

    override func setUpWithError() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-phone-05-queue-\(UUID().uuidString).sqlite")
        tempPath = url.path
    }

    override func tearDownWithError() throws {
        if let tempPath { try? FileManager.default.removeItem(atPath: tempPath) }
    }

    func testEnqueueAndCount() throws {
        let store = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
        let item = Self.makeItem()
        try store.enqueue(item)
        XCTAssertEqual(try store.pendingCount(), 1)
    }

    func testItemsSurviveReopen() throws {
        let item = Self.makeItem()
        do {
            let store = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
            try store.enqueue(item)
        }
        let store2 = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
        let pending = try store2.allPending()
        XCTAssertEqual(pending.count, 1)
        XCTAssertEqual(pending.first?.id, item.id)
    }

    func testDefaultQueuePathUsesApplicationSupport() throws {
        let queuePath = try SystemQueueStore.defaultPath()
        let cachePath = try SQLiteDatabase.defaultCachePath()

        XCTAssertTrue(queuePath.contains("Application Support"))
        XCTAssertTrue(cachePath.contains("Caches"))
        XCTAssertNotEqual(queuePath, cachePath)
    }

    func testLegacyCacheQueueRowsMigrateWithoutLoss() throws {
        let legacyPath = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-phone-07-legacy-\(UUID().uuidString).sqlite").path
        let targetPath = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-phone-07-target-\(UUID().uuidString).sqlite").path
        defer {
            try? FileManager.default.removeItem(atPath: legacyPath)
            try? FileManager.default.removeItem(atPath: targetPath)
        }

        let item = Self.makeItem()
        let legacy = try SystemQueueStore(db: SQLiteDatabase(path: legacyPath))
        try legacy.enqueue(item)

        let targetDB = try SQLiteDatabase(path: targetPath)
        _ = try SystemQueueStore(db: targetDB)
        try SystemQueueStore.migrateLegacyPendingUploads(from: legacyPath, into: targetDB)

        let migrated = try SystemQueueStore(db: SQLiteDatabase(path: targetPath)).allPending()
        XCTAssertEqual(migrated.count, 1)
        XCTAssertEqual(migrated.first?.id, item.id)
        XCTAssertEqual(migrated.first?.payload, item.payload)
        XCTAssertEqual(migrated.first?.kind, item.kind)
    }

    func testMarkFailedAdvancesBackoff() throws {
        let store = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
        let item = Self.makeItem()
        try store.enqueue(item)
        let now = Date()
        try store.markFailed(id: item.id, error: "boom", now: now)
        let after = try XCTUnwrap(store.allPending().first)
        XCTAssertEqual(after.retryCount, 1)
        XCTAssertGreaterThan(after.nextAttemptAt, now)
    }

    func testBackoffGrowsExponentially() {
        let now = Date()
        let t1 = SystemQueueStore.nextAttempt(after: now, retryCount: 1)
        let t2 = SystemQueueStore.nextAttempt(after: now, retryCount: 2)
        let t6 = SystemQueueStore.nextAttempt(after: now, retryCount: 6)
        let t10 = SystemQueueStore.nextAttempt(after: now, retryCount: 10)
        XCTAssertLessThan(t1, t2)
        XCTAssertLessThan(t2, t6)
        XCTAssertEqual(t6.timeIntervalSince(now), 3600, accuracy: 1) // cap
        XCTAssertEqual(t10.timeIntervalSince(now), 3600, accuracy: 1) // cap
    }

    func testNextDrainableHonorsBackoff() throws {
        let store = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
        let now = Date()
        let immediate = Self.makeItem(nextAttemptAt: now.addingTimeInterval(-1))
        let future = Self.makeItem(nextAttemptAt: now.addingTimeInterval(120))
        try store.enqueue(immediate)
        try store.enqueue(future)
        let drainable = try store.nextDrainable(now: now)
        XCTAssertEqual(drainable.count, 1)
        XCTAssertEqual(drainable.first?.id, immediate.id)
    }

    func testMarkSucceededRemoves() throws {
        let store = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
        let item = Self.makeItem()
        try store.enqueue(item)
        try store.markSucceeded(id: item.id)
        XCTAssertEqual(try store.pendingCount(), 0)
    }

    func testObserveEmitsCurrentAndAfterChanges() async throws {
        let store = try SystemQueueStore(db: SQLiteDatabase(path: tempPath))
        let item = Self.makeItem()

        let task = Task<[Int], Never> {
            var seen: [Int] = []
            for await count in store.observe() {
                seen.append(count)
                if seen.count >= 2 { break }
            }
            return seen
        }

        // Give the stream time to emit the initial 0, then enqueue.
        try await Task.sleep(nanoseconds: 50_000_000)
        try store.enqueue(item)
        let seen = await task.value
        XCTAssertEqual(seen.first, 0)
        XCTAssertEqual(seen.last, 1)
    }

    // MARK: - Helpers

    static func makeItem(
        nextAttemptAt: Date = Date()
    ) -> PendingUpload {
        let kind = PendingUploadKind.assetUpload(filename: "x.png", mimeType: "image/png", createSource: true)
        let metadata = (try? kind.encodedMetadata()) ?? Data()
        return PendingUpload(
            id: UUID(),
            kind: kind,
            payload: Data([0xAB, 0xCD]),
            metadata: metadata,
            retryCount: 0,
            lastError: nil,
            createdAt: Date(),
            nextAttemptAt: nextAttemptAt
        )
    }
}
