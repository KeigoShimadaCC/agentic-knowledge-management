import Foundation

struct ProjectAPI: Sendable {
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

    func list(limit: Int = 50, offset: Int = 0, status: String? = nil) async throws -> PaginatedResponseDTO<ProjectDTO> {
        try prepare()
        return try await apiClient.request(
            .projects(limit: limit, offset: offset, status: status),
            body: nil as String?,
            auth: true
        )
    }

    func update(
        id: UUID,
        title: String?,
        description: String?,
        role: String?,
        organization: String?,
        problem: String?,
        actions: String?,
        results: String?,
        skills: [String]?,
        status: String?,
        tags: [String]?
    ) async throws -> ProjectDTO {
        try prepare()
        let body = ProjectUpdateRequest(
            title: title,
            description: description,
            role: role,
            organization: organization,
            problem: problem,
            actions: actions,
            results: results,
            skills: skills,
            status: status,
            tags: tags
        )
        return try await apiClient.request(.updateProject(id: id), body: body, auth: true)
    }
}
