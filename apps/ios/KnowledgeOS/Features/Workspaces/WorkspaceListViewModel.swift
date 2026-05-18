import Foundation
import Observation

@MainActor
@Observable
final class WorkspaceListViewModel {
    private let api: WorkspaceAPI
    private(set) var workspaces: [WorkspaceDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: WorkspaceAPI = WorkspaceAPI()) {
        self.api = api
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let response = try await api.list()
            workspaces = response.items
        } catch {
            errorMessage = workspaceErrorMessage(error)
        }
    }
}

@MainActor
@Observable
final class WorkspaceDetailViewModel {
    private let api: WorkspaceAPI
    private(set) var workspace: WorkspaceDTO?
    private(set) var isLoading = false
    private(set) var isSaving = false
    private(set) var errorMessage: String?

    init(api: WorkspaceAPI = WorkspaceAPI()) {
        self.api = api
    }

    func load(id: UUID) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            workspace = try await api.get(id: id)
        } catch {
            errorMessage = workspaceErrorMessage(error)
        }
    }

    func update(name: String, description: String?, isPinned: Bool) async {
        guard let workspace else { return }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        do {
            self.workspace = try await api.update(
                id: workspace.id,
                name: name,
                description: description,
                layout: nil,
                isPinned: isPinned
            )
        } catch {
            errorMessage = workspaceErrorMessage(error)
        }
    }
}

func workspaceErrorMessage(_ error: Error) -> String {
    if let apiError = error as? APIError {
        return apiError.userMessage
    }
    return error.localizedDescription
}
