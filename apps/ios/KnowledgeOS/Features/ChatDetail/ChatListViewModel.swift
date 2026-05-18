import Foundation
import Observation

@MainActor
@Observable
final class ChatListViewModel {
    private let api: ChatListAPI
    private(set) var chats: [ObjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ChatListAPI = ChatListAPI()) {
        self.api = api
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            chats = try await api.list().items
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
