import Foundation
import Observation

@MainActor
@Observable
final class ProjectDetailViewModel {
    private let api: ReadAPI
    private(set) var project: ProjectDTO?
    private(set) var related: [RelatedObjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
    }

    func load(id: UUID) async {
        guard project?.id != id else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            async let projectResult = api.project(id: id)
            async let relatedResult = api.relatedObjects(id: id)
            project = try await projectResult
            related = (try? await relatedResult) ?? []
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
