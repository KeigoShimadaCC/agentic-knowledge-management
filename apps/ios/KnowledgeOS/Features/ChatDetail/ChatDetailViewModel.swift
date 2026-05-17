import Foundation
import Observation

@MainActor
@Observable
final class ChatDetailViewModel {
    private let api: ReadAPI
    private(set) var chat: ChatDTO?
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
    }

    func load(id: UUID) async {
        guard chat?.id != id else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            chat = try await api.chat(id: id)
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
