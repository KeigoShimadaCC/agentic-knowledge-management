import Foundation

struct AIAPI: Sendable {
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

    func answer(query: String, limit: Int = 5) async throws -> AnswerResponseDTO {
        try prepare()
        let request = AnswerRequest(
            q: query,
            kind: nil,
            limit: limit,
            objectIds: nil,
            useWebSearch: false
        )
        return try await apiClient.request(.aiAnswer, body: request, auth: true)
    }

    func summarize(objectId: UUID, force: Bool = false) async throws -> SummarizeResponseDTO {
        try prepare()
        let request = SummarizeRequest(objectId: objectId, force: force)
        return try await apiClient.request(.aiSummarize, body: request, auth: true)
    }

    func suggestLinks(objectId: UUID, limit: Int = 5) async throws -> SuggestLinksResponseDTO {
        try prepare()
        let request = SuggestLinksRequest(objectId: objectId, limit: limit)
        return try await apiClient.request(.aiSuggestLinks, body: request, auth: true)
    }
}
