import Foundation
import Observation

@MainActor
@Observable
final class ChatDetailViewModel {
    private let api: CachedReadAPI
    private(set) var chat: ChatDTO?
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
        guard chat?.id != id else { return }
        isLoading = true
        errorMessage = nil
        var sawAnything = false
        defer { isLoading = false }

        for await result in api.chat(id: id) {
            switch result {
            case let .success(value):
                chat = value
                errorMessage = nil
                sawAnything = true
            case let .failure(error):
                if !sawAnything { errorMessage = error.userMessage }
            }
        }
    }
}
