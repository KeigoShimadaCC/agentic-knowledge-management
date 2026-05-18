import XCTest
@testable import KnowledgeOS

@MainActor
final class CapturePersistenceTests: XCTestCase {
    func testServerErrorOnUploadEnqueuesPending() async throws {
        let queue = InMemoryQueueStore()
        let api = StubCaptureAPI(uploadResult: .failure(.serverError))
        let vm = CaptureViewModel(api: api, queueStore: queue)

        vm.enqueueUpload(data: Data([0x01, 0x02]), filename: "x.png", mimeType: "image/png")
        await vm.uploadQueuedItems()

        XCTAssertEqual(try queue.pendingCount(), 1)
        XCTAssertEqual(vm.uploads.first?.state, .pending)
    }

    func testValidationErrorDoesNotEnqueue() async throws {
        let queue = InMemoryQueueStore()
        let api = StubCaptureAPI(uploadResult: .failure(.validation("bad mime")))
        let vm = CaptureViewModel(api: api, queueStore: queue)

        vm.enqueueUpload(data: Data([0x01, 0x02]), filename: "x.png", mimeType: "image/png")
        await vm.uploadQueuedItems()

        XCTAssertEqual(try queue.pendingCount(), 0)
        if case let .failed(message) = vm.uploads.first?.state {
            XCTAssertEqual(message, APIError.validation("bad mime").userMessage)
        } else {
            XCTFail("expected failed state")
        }
    }

    func testQuickNoteServerErrorEnqueues() async throws {
        let queue = InMemoryQueueStore()
        let api = StubCaptureAPI(noteResult: .failure(.serverError))
        let vm = CaptureViewModel(api: api, queueStore: queue)

        await vm.saveQuickNote(title: "Hi", body: "Hello")

        XCTAssertEqual(try queue.pendingCount(), 1)
        XCTAssertNotNil(vm.noteError)
    }

    func testReadAPIPersistenceForCaptureRetry() async throws {
        // Round-trip a quick-note PageCreateRequest through the queue.
        let queue = InMemoryQueueStore()
        let api = StubCaptureAPI(noteResult: .failure(.serverError))
        let vm = CaptureViewModel(api: api, queueStore: queue)

        await vm.saveQuickNote(title: "T", body: "body line 1")
        let pending = try queue.allPending()
        XCTAssertEqual(pending.count, 1)
        let decoded = try JSONCoding.decoder.decode(PageCreateRequest.self, from: pending[0].payload)
        XCTAssertEqual(decoded.title, "T")
    }
}

// MARK: - StubCaptureAPI

private struct StubCaptureAPI: CaptureAPIProtocol, Sendable {
    var noteResult: Result<PageCreateResponseDTO, APIError> = .failure(.serverError)
    var uploadResult: Result<AssetSourceUploadResponseDTO, APIError> = .failure(.serverError)
    var sourceResult: Result<SourceDTO, APIError> = .failure(.notFound)

    func createQuickNote(title: String, body: String) async throws -> PageCreateResponseDTO {
        try noteResult.get()
    }
    func upload(data: Data, filename: String, mimeType: String) async throws -> AssetSourceUploadResponseDTO {
        try uploadResult.get()
    }
    func source(id: UUID) async throws -> SourceDTO {
        try sourceResult.get()
    }
}
