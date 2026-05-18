import Foundation

struct ObjectLifecycleAPI: Sendable {
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

    func trashObjects(page: Int = 1, limit: Int = 25) async throws -> PaginatedResponseDTO<ObjectDTO> {
        try prepare()
        return try await apiClient.request(.trashObjects(page: page, limit: limit), body: nil as String?, auth: true)
    }

    func archiveObject(id: UUID) async throws -> ObjectDTO {
        try prepare()
        return try await apiClient.request(.archiveObject(id: id), body: nil as String?, auth: true)
    }

    func moveObjectToTrash(id: UUID) async throws -> ObjectDTO {
        try prepare()
        return try await apiClient.request(.deleteObject(id: id), body: nil as String?, auth: true)
    }

    func restoreObject(id: UUID) async throws -> ObjectDTO {
        try prepare()
        return try await apiClient.request(.restoreObject(id: id), body: nil as String?, auth: true)
    }
}
