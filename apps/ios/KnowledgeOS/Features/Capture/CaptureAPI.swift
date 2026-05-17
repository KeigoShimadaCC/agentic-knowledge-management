import Foundation

protocol CaptureAPIProtocol: Sendable {
    func createQuickNote(title: String, body: String) async throws -> PageCreateResponseDTO
    func upload(data: Data, filename: String, mimeType: String) async throws -> AssetSourceUploadResponseDTO
    func source(id: UUID) async throws -> SourceDTO
}

struct KnowledgeOSCaptureAPI: CaptureAPIProtocol {
    private let apiClient: any APIClientProtocol

    init(apiClient: any APIClientProtocol) {
        self.apiClient = apiClient
    }

    func createQuickNote(title: String, body: String) async throws -> PageCreateResponseDTO {
        let request = PageCreateRequest(
            title: title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "Quick note" : title,
            contentJson: Self.tiptapDocument(from: body)
        )
        return try await apiClient.request(.createPage, body: request, auth: true)
    }

    func upload(data: Data, filename: String, mimeType: String) async throws -> AssetSourceUploadResponseDTO {
        let multipart = MultipartUpload(filename: filename, mimeType: mimeType, fileData: data)
        let response = try await apiClient.uploadMultipart(
            .assetUpload(createSource: true),
            upload: multipart,
            auth: true
        )
        do {
            return try JSONCoding.decoder.decode(AssetSourceUploadResponseDTO.self, from: response)
        } catch {
            throw APIError.decodingFailed(error.localizedDescription)
        }
    }

    func source(id: UUID) async throws -> SourceDTO {
        try await apiClient.request(.source(id: id), body: nil as String?, auth: true)
    }

    static func tiptapDocument(from body: String) -> [String: AnyCodable] {
        let paragraphs = body
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        let content = (paragraphs.isEmpty ? [""] : paragraphs).map { paragraph in
            [
                "type": "paragraph",
                "content": paragraph.isEmpty ? [] : [
                    [
                        "type": "text",
                        "text": paragraph,
                    ],
                ],
            ] as [String: Any]
        }

        return [
            "type": AnyCodable("doc"),
            "content": AnyCodable(content),
        ]
    }
}
