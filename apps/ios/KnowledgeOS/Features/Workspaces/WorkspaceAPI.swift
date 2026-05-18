import Foundation

struct WorkspaceAPI: Sendable {
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

    func list(limit: Int = 50, offset: Int = 0, pinnedOnly: Bool = false) async throws -> PaginatedResponseDTO<WorkspaceDTO> {
        try prepare()
        return try await apiClient.request(
            .workspaces(limit: limit, offset: offset, pinnedOnly: pinnedOnly),
            body: nil as String?,
            auth: true
        )
    }

    func get(id: UUID) async throws -> WorkspaceDTO {
        try prepare()
        return try await apiClient.request(.workspace(id: id), body: nil as String?, auth: true)
    }

    func update(
        id: UUID,
        name: String?,
        description: String?,
        layout: WorkspaceLayoutDTO?,
        isPinned: Bool?
    ) async throws -> WorkspaceDTO {
        try prepare()
        let body = WorkspaceUpdateRequest(
            name: name,
            description: description,
            layout: layout,
            isPinned: isPinned
        )
        return try await apiClient.request(.updateWorkspace(id: id), body: body, auth: true)
    }
}
