import Foundation

struct ChatSummaryAPI: Sendable {
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

    func load(chatId: UUID) async throws -> StructuredSummaryPreviewDTO {
        try prepare()
        return try await apiClient.request(
            .chatStructuredSummary(id: chatId),
            body: nil as String?,
            auth: true
        )
    }

    func generate(chatId: UUID) async throws -> StructuredSummaryPreviewDTO {
        try prepare()
        return try await apiClient.request(
            .generateChatStructuredSummary(id: chatId),
            body: nil as String?,
            auth: true
        )
    }
}
