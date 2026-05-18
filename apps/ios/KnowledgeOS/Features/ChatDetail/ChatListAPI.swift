import Foundation

struct ChatListAPI: Sendable {
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

    func list(page: Int = 1, limit: Int = 50) async throws -> PaginatedResponseDTO<ObjectDTO> {
        try prepare()
        return try await apiClient.request(
            .objects(page: page, limit: limit, kind: "chat"),
            body: nil as String?,
            auth: true
        )
    }
}
