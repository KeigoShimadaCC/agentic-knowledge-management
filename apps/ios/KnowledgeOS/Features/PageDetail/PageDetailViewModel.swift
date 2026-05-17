import Foundation
import Observation

@MainActor
@Observable
final class PageDetailViewModel {
    private let api: ReadAPI
    private(set) var page: PageDTO?
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
    }

    func load(id: UUID) async {
        guard page?.id != id else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            page = try await api.page(id: id)
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
