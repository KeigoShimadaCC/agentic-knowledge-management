import Foundation
import Observation

@MainActor
@Observable
final class ProjectListViewModel {
    private let api: ProjectAPI
    private(set) var projects: [ProjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ProjectAPI = ProjectAPI()) {
        self.api = api
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let response = try await api.list()
            projects = response.items
        } catch {
            errorMessage = projectErrorMessage(error)
        }
    }
}

func projectErrorMessage(_ error: Error) -> String {
    if let apiError = error as? APIError {
        return apiError.userMessage
    }
    return error.localizedDescription
}
