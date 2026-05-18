import Foundation

struct EditAPI: Sendable {
    private let apiClient: any APIClientProtocol
    private let keychain: any KeychainStore

    init(
        apiClient: any APIClientProtocol = APIClient(),
        keychain: any KeychainStore = SystemKeychainStore()
    ) {
        self.apiClient = apiClient
        self.keychain = keychain
    }

    private func prepare() throws {
        if apiClient.bearerToken == nil {
            apiClient.setBearerToken(try keychain.readToken())
        }
    }

    func updateObject(
        id: UUID,
        title: String?,
        description: String?,
        tags: [String]?
    ) async throws -> ObjectDTO {
        try prepare()
        let body = ObjectUpdateRequest(title: title, description: description, tags: tags)
        return try await apiClient.request(.updateObject(id: id), body: body, auth: true)
    }

    func updatePage(
        id: UUID,
        title: String?,
        contentJson: [String: AnyCodable]?,
        contentText: String?,
        expectedVersion: Int?
    ) async throws -> PageDTO {
        try prepare()
        let body = PageUpdateRequest(
            title: title,
            contentJson: contentJson,
            contentText: contentText,
            expectedVersion: expectedVersion
        )
        return try await apiClient.request(.updatePage(id: id), body: body, auth: true)
    }

    func page(id: UUID) async throws -> PageDTO {
        try prepare()
        return try await apiClient.request(.page(id: id), body: nil as String?, auth: true)
    }
}
