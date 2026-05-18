import XCTest
@testable import KnowledgeOS

@MainActor
final class QueueDrainerTests: XCTestCase {
    func testSuccessfulDrainRemovesItem() async throws {
        let queue = InMemoryQueueStore()
        let item = QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1))
        try queue.enqueue(item)

        let stub = StubAPIClient(behavior: .succeedWith(Data("ok".utf8)))
        let drainer = QueueDrainer(queue: queue, apiClient: stub, keychain: InMemoryKeychainStub())

        let summary = await drainer.drain()
        XCTAssertEqual(summary.succeeded, 1)
        XCTAssertEqual(summary.failed, 0)
        XCTAssertEqual(try queue.pendingCount(), 0)
    }

    func testFailedDrainMarksFailed() async throws {
        let queue = InMemoryQueueStore()
        let item = QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1))
        try queue.enqueue(item)

        let stub = StubAPIClient(behavior: .failWith(.serverError))
        let drainer = QueueDrainer(queue: queue, apiClient: stub, keychain: InMemoryKeychainStub())

        let summary = await drainer.drain()
        XCTAssertEqual(summary.failed, 1)
        XCTAssertEqual(summary.succeeded, 0)
        let after = try XCTUnwrap(queue.allPending().first)
        XCTAssertEqual(after.retryCount, 1)
    }

    func testDeadlineStopsDraining() async throws {
        let queue = InMemoryQueueStore()
        for _ in 0..<5 {
            try queue.enqueue(QueueStoreTests.makeItem(nextAttemptAt: Date().addingTimeInterval(-1)))
        }
        // Stub returns success but we set deadline in the past so we stop after attempt 0/1.
        let stub = StubAPIClient(behavior: .succeedWith(Data()))
        let drainer = QueueDrainer(queue: queue, apiClient: stub, keychain: InMemoryKeychainStub())

        let summary = await drainer.drain(deadline: Date().addingTimeInterval(-10))
        XCTAssertLessThan(summary.attempted, 5)
    }
}
