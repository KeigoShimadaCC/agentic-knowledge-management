import Foundation
import Observation

@MainActor
@Observable
final class TrashViewModel {
    private let api: ObjectLifecycleAPI
    private(set) var objects: [ObjectDTO] = []
    private(set) var isLoading = false
    private(set) var errorMessage: String?
    private(set) var isRestoring: UUID?

    init(api: ObjectLifecycleAPI = ObjectLifecycleAPI()) {
        self.api = api
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let response = try await api.trashObjects()
            objects = response.items
        } catch {
            errorMessage = objectLifecycleErrorMessage(error)
        }
    }

    func restore(_ object: ObjectDTO) async {
        isRestoring = object.id
        defer { isRestoring = nil }

        do {
            _ = try await api.restoreObject(id: object.id)
            objects.removeAll { $0.id == object.id }
        } catch {
            errorMessage = objectLifecycleErrorMessage(error)
        }
    }
}

func objectLifecycleErrorMessage(_ error: Error) -> String {
    if let apiError = error as? APIError {
        return apiError.userMessage
    }
    return error.localizedDescription
}
