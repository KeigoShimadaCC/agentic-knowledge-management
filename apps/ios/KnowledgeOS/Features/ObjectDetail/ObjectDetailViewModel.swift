import Foundation
import Observation

@MainActor
@Observable
final class ObjectDetailViewModel {
    private let api: CachedReadAPI
    private let lifecycleAPI: ObjectLifecycleAPI
    private(set) var object: ObjectDTO?
    private(set) var isLoading = false
    private(set) var isMutating = false
    private(set) var errorMessage: String?

    init(api: CachedReadAPI? = nil, lifecycleAPI: ObjectLifecycleAPI = ObjectLifecycleAPI()) {
        if let api {
            self.api = api
        } else {
            self.api = CachedReadAPI(cache: (try? SystemCacheStore()) ?? InMemoryCacheStore())
        }
        self.lifecycleAPI = lifecycleAPI
    }

    func load(id: UUID) async {
        guard object?.id != id else { return }
        isLoading = true
        errorMessage = nil
        var sawAnything = false
        defer { isLoading = false }

        for await result in api.object(id: id) {
            switch result {
            case let .success(value):
                object = value
                errorMessage = nil
                sawAnything = true
            case let .failure(error):
                if !sawAnything { errorMessage = error.userMessage }
            }
        }
    }

    func apply(updated: ObjectDTO) {
        object = updated
    }

    func archiveCurrentObject() async {
        guard let object else { return }
        isMutating = true
        errorMessage = nil
        defer { isMutating = false }

        do {
            self.object = try await lifecycleAPI.archiveObject(id: object.id)
        } catch {
            errorMessage = objectLifecycleErrorMessage(error)
        }
    }

    func moveCurrentObjectToTrash() async {
        guard let object else { return }
        isMutating = true
        errorMessage = nil
        defer { isMutating = false }

        do {
            self.object = try await lifecycleAPI.moveObjectToTrash(id: object.id)
        } catch {
            errorMessage = objectLifecycleErrorMessage(error)
        }
    }
}
