import Foundation
import Observation

@MainActor
@Observable
final class ChatDetailViewModel {
    private let api: CachedReadAPI
    private let summaryAPI: ChatSummaryAPI
    private(set) var chat: ChatDTO?
    private(set) var summaryPreview: StructuredSummaryPreviewDTO?
    private(set) var isLoading = false
    private(set) var isSummaryLoading = false
    private(set) var errorMessage: String?
    private(set) var summaryErrorMessage: String?

    init(api: CachedReadAPI? = nil, summaryAPI: ChatSummaryAPI = ChatSummaryAPI()) {
        if let api {
            self.api = api
        } else {
            self.api = CachedReadAPI(cache: (try? SystemCacheStore()) ?? InMemoryCacheStore())
        }
        self.summaryAPI = summaryAPI
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

    func loadSummary(id: UUID) async {
        isSummaryLoading = true
        summaryErrorMessage = nil
        defer { isSummaryLoading = false }

        do {
            summaryPreview = try await summaryAPI.load(chatId: id)
        } catch {
            summaryErrorMessage = readErrorMessage(error)
        }
    }

    func generateSummary(id: UUID) async {
        isSummaryLoading = true
        summaryErrorMessage = nil
        defer { isSummaryLoading = false }

        do {
            summaryPreview = try await summaryAPI.generate(chatId: id)
        } catch {
            summaryErrorMessage = readErrorMessage(error)
        }
    }
}
