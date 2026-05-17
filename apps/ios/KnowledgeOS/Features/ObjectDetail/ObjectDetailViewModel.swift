import Foundation
import Observation

@MainActor
@Observable
final class ObjectDetailViewModel {
    private let api: ReadAPI
    private(set) var object: ObjectDTO?
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
    }

    func load(id: UUID) async {
        guard object?.id != id else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            object = try await api.object(id: id)
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }

    func apply(updated: ObjectDTO) {
        object = updated
    }
}
