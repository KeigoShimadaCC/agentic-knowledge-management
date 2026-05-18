import Foundation
import Observation

@MainActor
@Observable
final class ObjectDetailViewModel {
    private let api: CachedReadAPI
    private(set) var object: ObjectDTO?
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
}
