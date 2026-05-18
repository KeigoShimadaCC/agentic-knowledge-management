import Foundation
import Observation

@MainActor
@Observable
final class HomeViewModel {
    private let api: CachedReadAPI
    private(set) var objects: [ObjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?
    private var page = 1
    private var canLoadMore = true

    init(api: CachedReadAPI? = nil) {
        if let api {
            self.api = api
        } else {
            self.api = CachedReadAPI(cache: (try? SystemCacheStore()) ?? InMemoryCacheStore())
        }
    }

    func loadInitial() async {
        guard objects.isEmpty else { return }
        await refresh()
    }

    func refresh() async {
        page = 1
        canLoadMore = true
        await load(reset: true)
    }

    func loadMoreIfNeeded(current: ObjectDTO) async {
        guard canLoadMore, !isLoading, current.id == objects.last?.id else { return }
        page += 1
        await load(reset: false)
    }

    private func load(reset: Bool) async {
        isLoading = true
        errorMessage = nil
        var sawAnything = false
        defer { isLoading = false }

        for await result in api.recentObjects(page: page) {
            switch result {
            case let .success(response):
                objects = reset ? response.items : (sawAnything ? objects : objects + response.items)
                // For pagination: only append once. If we saw a cached then a fresh, both
                // overwrite the page slice; we treat the fresh as canonical.
                if reset {
                    objects = response.items
                } else if !sawAnything {
                    objects.append(contentsOf: response.items)
                } else {
                    // Subsequent yields for the same page replace the tail we just appended.
                    let tail = objects.suffix(response.items.count)
                    if Array(tail) != response.items {
                        objects.removeLast(tail.count)
                        objects.append(contentsOf: response.items)
                    }
                }
                canLoadMore = response.page < response.pages
                errorMessage = nil
                sawAnything = true
            case let .failure(error):
                if !sawAnything {
                    if !reset { page = max(1, page - 1) }
                    errorMessage = error.userMessage
                }
            }
        }
    }
}
