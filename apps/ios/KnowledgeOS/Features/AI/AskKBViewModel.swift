import Foundation
import Observation

@MainActor
@Observable
final class AskKBViewModel {
    var query: String = ""
    private(set) var answer: AnswerResponseDTO?
    private(set) var isLoading: Bool = false
    private(set) var errorMessage: String?
    private(set) var aiDisabled: Bool = false

    private let api: AIAPI

    init(api: AIAPI = AIAPI()) {
        self.api = api
    }

    var canSubmit: Bool {
        !aiDisabled && !isLoading && !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func ask() async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        isLoading = true
        errorMessage = nil
        answer = nil
        defer { isLoading = false }
        do {
            answer = try await api.answer(query: trimmed)
        } catch let error as APIError {
            if case .aiDisabled = error {
                aiDisabled = true
            }
            errorMessage = error.userMessage
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func setAIDisabled(_ disabled: Bool) {
        aiDisabled = disabled
    }

    func reset() {
        query = ""
        answer = nil
        errorMessage = nil
    }
}
