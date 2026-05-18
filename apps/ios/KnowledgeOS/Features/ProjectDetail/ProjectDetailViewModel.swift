import Foundation
import Observation

@MainActor
@Observable
final class ProjectDetailViewModel {
    private let api: CachedReadAPI
    private let projectAPI: ProjectAPI
    private(set) var project: ProjectDTO?
    private(set) var related: [RelatedObjectDTO] = []
    private(set) var isLoading = false
    private(set) var isSaving = false
    private(set) var errorMessage: String?

    init(api: CachedReadAPI? = nil, projectAPI: ProjectAPI = ProjectAPI()) {
        if let api {
            self.api = api
        } else {
            self.api = CachedReadAPI(cache: (try? SystemCacheStore()) ?? InMemoryCacheStore())
        }
        self.projectAPI = projectAPI
    }

    func load(id: UUID) async {
        guard project?.id != id else { return }
        isLoading = true
        errorMessage = nil
        var sawAnything = false
        defer { isLoading = false }

        for await result in api.project(id: id) {
            switch result {
            case let .success(value):
                project = value
                errorMessage = nil
                sawAnything = true
                // related is a pass-through; kick it off alongside the fresh project.
                related = (try? await api.relatedObjects(id: id)) ?? []
            case let .failure(error):
                if !sawAnything { errorMessage = error.userMessage }
            }
        }
    }

    func update(
        title: String,
        description: String?,
        role: String?,
        organization: String?,
        status: String,
        skills: [String]
    ) async {
        guard let project else { return }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        do {
            self.project = try await projectAPI.update(
                id: project.id,
                title: title,
                description: description,
                role: role,
                organization: organization,
                problem: nil,
                actions: nil,
                results: nil,
                skills: skills,
                status: status,
                tags: nil
            )
        } catch {
            errorMessage = projectErrorMessage(error)
        }
    }
}
