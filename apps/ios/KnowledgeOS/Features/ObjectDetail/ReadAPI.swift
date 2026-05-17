import Foundation

struct ObjectRoute: Hashable, Identifiable {
    let id: UUID
    let kind: String
}

struct ReadAPI: Sendable {
    private let apiClient: any APIClientProtocol
    private let keychain: any KeychainStore

    init(
        apiClient: any APIClientProtocol = APIClient(),
        keychain: any KeychainStore = SystemKeychainStore()
    ) {
        self.apiClient = apiClient
        self.keychain = keychain
    }

    func prepare() throws {
        if apiClient.bearerToken == nil {
            apiClient.setBearerToken(try keychain.readToken())
        }
    }

    func recentObjects(page: Int, limit: Int = 25) async throws -> PaginatedResponseDTO<ObjectDTO> {
        try prepare()
        return try await apiClient.request(.objects(page: page, limit: limit), body: nil as String?, auth: true)
    }

    func object(id: UUID) async throws -> ObjectDTO {
        try prepare()
        return try await apiClient.request(.object(id: id), body: nil as String?, auth: true)
    }

    func page(id: UUID) async throws -> PageDTO {
        try prepare()
        return try await apiClient.request(.page(id: id), body: nil as String?, auth: true)
    }

    func source(id: UUID) async throws -> SourceDTO {
        try prepare()
        return try await apiClient.request(.source(id: id), body: nil as String?, auth: true)
    }

    func sourceText(id: UUID) async throws -> String {
        try prepare()
        let data = try await apiClient.requestData(sourceTextEndpoint(id: id), body: nil as String?, auth: true)
        return String(decoding: data, as: UTF8.self)
    }

    func sourceThumbnail(id: UUID) async throws -> Data {
        try prepare()
        return try await apiClient.requestData(sourceThumbnailEndpoint(id: id), body: nil as String?, auth: true)
    }

    func sourceDownloadURL(id: UUID) -> URL? {
        URL(string: sourceDownloadEndpoint(id: id).relativePath, relativeTo: ServerConfig.shared.baseURL)
    }

    func chat(id: UUID) async throws -> ChatDTO {
        try prepare()
        return try await apiClient.request(.chat(id: id), body: nil as String?, auth: true)
    }

    func project(id: UUID) async throws -> ProjectDTO {
        try prepare()
        return try await apiClient.request(.project(id: id), body: nil as String?, auth: true)
    }

    func relatedObjects(id: UUID) async throws -> [RelatedObjectDTO] {
        try prepare()
        return try await apiClient.request(relatedObjectsEndpoint(id: id), body: nil as String?, auth: true)
    }

    func search(query: String, limit: Int = 25) async throws -> HybridSearchResponseDTO {
        try prepare()
        let request = HybridSearchRequest(
            q: query,
            kind: nil,
            sourceType: nil,
            limit: limit,
            debug: false,
            objectIds: nil
        )
        return try await apiClient.request(.hybridSearch, body: request, auth: true)
    }

    private func sourceTextEndpoint(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/sources/\(id.uuidString)/text", method: .get)
    }

    private func sourceThumbnailEndpoint(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/sources/\(id.uuidString)/thumbnail", method: .get)
    }

    private func sourceDownloadEndpoint(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/sources/\(id.uuidString)/download", method: .get)
    }

    private func relatedObjectsEndpoint(id: UUID, limit: Int = 20) -> APIEndpoint {
        APIEndpoint(
            path: "/api/v1/objects/\(id.uuidString)/related",
            method: .get,
            queryItems: [URLQueryItem(name: "limit", value: String(limit))]
        )
    }
}

func readErrorMessage(_ error: Error) -> String {
    if let apiError = error as? APIError {
        return apiError.userMessage
    }
    return error.localizedDescription
}
