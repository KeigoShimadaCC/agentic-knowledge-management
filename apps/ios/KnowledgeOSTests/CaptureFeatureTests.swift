import XCTest
@testable import KnowledgeOS

@MainActor
final class CaptureFeatureTests: XCTestCase {
    func testTiptapDocumentWrapsPlainTextParagraphs() throws {
        let document = KnowledgeOSCaptureAPI.tiptapDocument(from: "First\n\nSecond")

        XCTAssertEqual(document["type"]?.value as? String, "doc")
        let content = try XCTUnwrap(document["content"]?.value as? [[String: Any]])
        XCTAssertEqual(content.count, 2)
        XCTAssertEqual(content[0]["type"] as? String, "paragraph")
    }

    func testSaveQuickNoteRequiresBody() async {
        let api = MockCaptureAPI()
        let model = CaptureViewModel(api: api)

        await model.saveQuickNote(title: "Ignored", body: "   ")

        XCTAssertEqual(model.noteError, "Add note text before saving.")
        XCTAssertNil(model.createdNote)
    }

    func testUploadFailureCanRetryFromInMemoryQueue() async {
        let api = MockCaptureAPI()
        api.uploadResults = [
            .failure(APIError.networkUnavailable),
            .success(.sample(source: .sample(ingestionStatus: "pending"))),
        ]
        let model = CaptureViewModel(api: api)
        model.enqueueUpload(data: Data([1, 2, 3]), filename: "photo.jpg", mimeType: "image/jpeg")

        await model.uploadQueuedItems()
        guard let failed = model.uploads.first else {
            return XCTFail("Expected queued upload")
        }
        if case .failed = failed.state {
            XCTAssertEqual(api.uploadCallCount, 1)
        } else {
            XCTFail("Expected failed upload")
        }

        await model.retry(itemID: failed.id)

        XCTAssertEqual(api.uploadCallCount, 2)
        guard let retried = model.uploads.first else {
            return XCTFail("Expected retried upload")
        }
        if case .uploaded = retried.state {
            XCTAssertEqual(retried.progress, 1)
        } else {
            XCTFail("Expected successful retry")
        }
    }

    func testRefreshMarksReadySource() async {
        let sourceID = UUID()
        let api = MockCaptureAPI()
        api.sourceResult = .sample(id: sourceID, ingestionStatus: "ready")
        let model = CaptureViewModel(api: api)
        model.enqueueUpload(data: Data([1]), filename: "doc.pdf", mimeType: "application/pdf")
        api.uploadResults = [.success(.sample(source: .sample(id: sourceID, ingestionStatus: "pending")))]
        await model.uploadQueuedItems()

        let source = await model.refresh(sourceID: sourceID)

        XCTAssertEqual(source?.ingestionStatus, "ready")
        guard let item = model.uploads.first else {
            return XCTFail("Expected upload item")
        }
        if case .ready(sourceID) = item.state {
            XCTAssertEqual(sourceID, source?.id)
        } else {
            XCTFail("Expected ready upload state")
        }
    }

    func testCreatedPageWebURLUsesWebPortAndPageRoute() throws {
        let id = UUID()
        let url = try XCTUnwrap(
            CaptureViewModel.webPageURL(for: id, apiBaseURL: URL(string: "http://127.0.0.1:8001")!)
        )

        XCTAssertEqual(url.absoluteString, "http://127.0.0.1:3000/app/pages/\(id.uuidString)")
    }
}

private final class MockCaptureAPI: CaptureAPIProtocol, @unchecked Sendable {
    var uploadResults: [Result<AssetSourceUploadResponseDTO, Error>] = []
    var sourceResult: SourceDTO = .sample(ingestionStatus: "pending")
    private(set) var uploadCallCount = 0

    func createQuickNote(title: String, body: String) async throws -> PageCreateResponseDTO {
        .sample(title: title)
    }

    func upload(data: Data, filename: String, mimeType: String) async throws -> AssetSourceUploadResponseDTO {
        uploadCallCount += 1
        guard !uploadResults.isEmpty else {
            return .sample(source: .sample(ingestionStatus: "pending"))
        }
        return try uploadResults.removeFirst().get()
    }

    func source(id: UUID) async throws -> SourceDTO {
        sourceResult
    }
}

private extension PageCreateResponseDTO {
    static func sample(title: String = "Quick note") -> PageCreateResponseDTO {
        PageCreateResponseDTO(
            object: .sample(kind: "page", title: title),
            page: PageDTO(
                id: UUID(),
                contentJson: [:],
                contentText: "",
                wordCount: 0,
                version: 1,
                createdAt: Date(),
                updatedAt: Date()
            )
        )
    }
}

private extension AssetSourceUploadResponseDTO {
    static func sample(source: SourceDTO) -> AssetSourceUploadResponseDTO {
        AssetSourceUploadResponseDTO(
            object: AssetDTO(
                id: UUID(),
                filename: "photo.jpg",
                contentType: "image/jpeg",
                sizeBytes: 3,
                sha256: "abc",
                storagePath: "assets/ab/abc/original.jpg",
                status: "stored",
                width: nil,
                height: nil,
                durationSecs: nil,
                createdAt: Date(),
                updatedAt: Date()
            ),
            source: source
        )
    }
}

private extension SourceDTO {
    static func sample(
        id: UUID = UUID(),
        ingestionStatus: String,
        errorMessage: String? = nil
    ) -> SourceDTO {
        SourceDTO(
            id: id,
            userId: UUID(),
            kind: "source",
            title: "Uploaded source",
            description: nil,
            tags: [],
            isPinned: false,
            isArchived: false,
            createdAt: Date(),
            updatedAt: Date(),
            deletedAt: nil,
            sourceType: "image",
            url: nil,
            assetId: UUID(),
            ingestionStatus: ingestionStatus,
            extractedText: nil,
            pageCount: nil,
            thumbnailPath: nil,
            previewData: nil,
            errorMessage: errorMessage
        )
    }
}

private extension ObjectDTO {
    static func sample(kind: String, title: String) -> ObjectDTO {
        ObjectDTO(
            id: UUID(),
            userId: UUID(),
            kind: kind,
            title: title,
            description: nil,
            tags: [],
            metadata: nil,
            isPinned: false,
            isArchived: false,
            aiGenerated: false,
            createdAt: Date(),
            updatedAt: Date(),
            deletedAt: nil
        )
    }
}
