import Foundation
import Observation

@MainActor
@Observable
final class PageDetailViewModel {
    private let api: CachedReadAPI
    private(set) var page: PageDTO?
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
        guard page?.id != id else { return }
        isLoading = true
        errorMessage = nil
        var sawAnything = false
        defer { isLoading = false }

        for await result in api.page(id: id) {
            switch result {
            case let .success(value):
                page = value
                errorMessage = nil
                sawAnything = true
            case let .failure(error):
                if !sawAnything { errorMessage = error.userMessage }
            }
        }
    }
}
