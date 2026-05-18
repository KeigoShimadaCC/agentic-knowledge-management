import Foundation
import Observation

@MainActor
@Observable
final class ProjectDetailViewModel {
    private let api: CachedReadAPI
    private(set) var project: ProjectDTO?
    private(set) var related: [RelatedObjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: CachedReadAPI? = nil) {
        if let api {
            self.api = api
        } else {
            self.api = CachedReadAPI(cache: (try? SystemCacheStore()) ?? InMemoryCacheStore())
        }
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
}
