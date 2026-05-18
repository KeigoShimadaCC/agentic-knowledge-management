import Foundation

struct GraphAPI: Sendable {
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

    func outgoingEdges(objectID: UUID) async throws -> [EdgeDTO] {
        try prepare()
        return try await apiClient.request(.objectEdges(id: objectID), body: nil as String?, auth: true)
    }

    func backlinks(objectID: UUID) async throws -> [EdgeDTO] {
        try prepare()
        return try await apiClient.request(.objectBacklinks(id: objectID), body: nil as String?, auth: true)
    }

    func createEdge(sourceID: UUID, targetID: UUID, kind: String) async throws -> EdgeMutationDTO {
        try prepare()
        let body = EdgeCreateRequest(
            sourceId: sourceID,
            targetId: targetID,
            kind: kind,
            weight: 1.0,
            metadata: [:]
        )
        return try await apiClient.request(.createEdge, body: body, auth: true)
    }

    func deleteEdge(id: UUID) async throws -> EdgeMutationDTO {
        try prepare()
        return try await apiClient.request(.deleteEdge(id: id), body: nil as String?, auth: true)
    }
}
