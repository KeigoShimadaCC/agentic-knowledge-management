import XCTest
@testable import KnowledgeOS

@MainActor
final class QueueConflictSurfaceTests: XCTestCase {
    func testConflictDrainMarksNeedsAttentionAndStopsRetry() async throws {
        let queue = InMemoryQueueStore()
        let item = QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1))
        try queue.enqueue(item)

        let stub = StubAPIClient(behavior: .failWith(.conflict("page changed")))
        let drainer = QueueDrainer(queue: queue, apiClient: stub, keychain: InMemoryKeychainStub())

        let summary = await drainer.drain()

        // First-pass classification: permanentFailed, transientFailed stays 0.
        XCTAssertEqual(summary.permanentFailed, 1)
        XCTAssertEqual(summary.transientFailed, 0)

        // Item is parked: still counted but excluded from drainable set.
        XCTAssertEqual(try queue.pendingCount(), 1)
        XCTAssertEqual(try queue.nextDrainable(now: Date().addingTimeInterval(60)).count, 0)

        // The parked row carries the error message and is flagged.
        let parked = try XCTUnwrap(queue.allPending().first)
        XCTAssertTrue(parked.needsAttention)
        XCTAssertEqual(parked.retryCount, 0, "needsAttention must not auto-increment retry_count")
    }

    func testValidationErrorIsPermanent() async throws {
        let queue = InMemoryQueueStore()
        try queue.enqueue(QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1)))
        let stub = StubAPIClient(behavior: .failWith(.validation("bad body")))
        let drainer = QueueDrainer(queue: queue, apiClient: stub, keychain: InMemoryKeychainStub())

        let summary = await drainer.drain()
        XCTAssertEqual(summary.permanentFailed, 1)
        XCTAssertTrue(try queue.allPending().first?.needsAttention ?? false)
    }

    func testServerErrorStillTreatedAsTransient() async throws {
        let queue = InMemoryQueueStore()
        try queue.enqueue(QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1)))
        let stub = StubAPIClient(behavior: .failWith(.serverError))
        let drainer = QueueDrainer(queue: queue, apiClient: stub, keychain: InMemoryKeychainStub())

        let summary = await drainer.drain()
        XCTAssertEqual(summary.transientFailed, 1)
        XCTAssertEqual(summary.permanentFailed, 0)
        XCTAssertFalse(try queue.allPending().first?.needsAttention ?? true)
    }

    func testRetryAfterClearNeedsAttentionDrains() async throws {
        let queue = InMemoryQueueStore()
        let item = QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1))
        try queue.enqueue(item)
        try queue.markNeedsAttention(id: item.id, error: "conflict")
        XCTAssertEqual(try queue.nextDrainable(now: Date()).count, 0)

        try queue.clearNeedsAttention(id: item.id)
        let drainable = try queue.nextDrainable(now: Date().addingTimeInterval(1))
        XCTAssertEqual(drainable.count, 1)
        XCTAssertFalse(drainable[0].needsAttention)
    }

    func testNeedsAttentionSurvivesReopen() throws {
        let path = FileManager.default.temporaryDirectory
            .appendingPathComponent("kos-needs-attention-\(UUID()).sqlite").path
        defer { try? FileManager.default.removeItem(atPath: path) }

        let item = QueueStoreTests.makeItem()
        do {
            let store = try SystemQueueStore(db: SQLiteDatabase(path: path))
            try store.enqueue(item)
            try store.markNeedsAttention(id: item.id, error: "conflict")
        }
        let store2 = try SystemQueueStore(db: SQLiteDatabase(path: path))
        let reopened = try XCTUnwrap(store2.allPending().first)
        XCTAssertTrue(reopened.needsAttention)
        XCTAssertEqual(reopened.lastError, "conflict")
    }

    func testIsPermanentClassification() {
        // Permanent: conflicts and 4xx that won't auto-resolve.
        XCTAssertTrue(QueueDrainer.isPermanent(.conflict("x")))
        XCTAssertTrue(QueueDrainer.isPermanent(.validation("x")))
        XCTAssertTrue(QueueDrainer.isPermanent(.forbidden))
        XCTAssertTrue(QueueDrainer.isPermanent(.notFound))
        XCTAssertTrue(QueueDrainer.isPermanent(.notAuthenticated))
        XCTAssertTrue(QueueDrainer.isPermanent(.aiDisabled))

        // Transient: worth retrying.
        XCTAssertFalse(QueueDrainer.isPermanent(.networkUnavailable))
        XCTAssertFalse(QueueDrainer.isPermanent(.serverError))
        XCTAssertFalse(QueueDrainer.isPermanent(.decodingFailed("x")))
    }
}
