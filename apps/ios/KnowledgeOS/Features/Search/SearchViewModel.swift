import Foundation
import Observation

@MainActor
@Observable
final class SearchViewModel {
    var query = ""
    private(set) var results: [HybridSearchResultDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    private let api: ReadAPI
    private var task: Task<Void, Never>?

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
    }

    func scheduleSearch(for value: String) {
        task?.cancel()
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            results = []
            errorMessage = nil
            isLoading = false
            return
        }

        task = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 350_000_000)
            guard !Task.isCancelled else { return }
            await self?.searchNow()
        }
    }

    func searchNow() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let response = try await api.search(query: trimmed)
            results = response.results
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
