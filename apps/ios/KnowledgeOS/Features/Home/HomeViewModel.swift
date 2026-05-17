import Foundation
import Observation

@MainActor
@Observable
final class HomeViewModel {
    private let api: ReadAPI
    private(set) var objects: [ObjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?
    private var page = 1
    private var canLoadMore = true

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
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
        defer { isLoading = false }

        do {
            let response = try await api.recentObjects(page: page)
            objects = reset ? response.items : objects + response.items
            canLoadMore = response.page < response.pages
        } catch {
            if !reset { page = max(1, page - 1) }
            errorMessage = readErrorMessage(error)
        }
    }
}
