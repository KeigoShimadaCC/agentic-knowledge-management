import SwiftUI

struct SuggestLinksSheet: View {
    let object: ObjectDTO
    var api: AIAPI = AIAPI()

    @Environment(\.dismiss) private var dismiss
    @State private var suggestions: [LinkSuggestionDTO] = []
    @State private var isLoading: Bool = true
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if isLoading {
                    ProgressView("Looking for related objects…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let message = errorMessage {
                    VStack(spacing: 8) {
                        Text(message)
                            .foregroundStyle(.red)
                            .multilineTextAlignment(.center)
                    }
                    .padding()
                    .accessibilityIdentifier("kos.ai.suggestError")
                } else if suggestions.isEmpty {
                    EmptyStateView(
                        title: "No suggestions",
                        message: "Nothing in your KB looked obviously related."
                    )
                } else {
                    List(suggestions, id: \.targetId) { suggestion in
                        NavigationLink(value: ObjectRoute(id: suggestion.targetId, kind: suggestion.targetKind)) {
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    ObjectKindBadge(kind: suggestion.targetKind)
                                    Spacer()
                                    Text(String(format: "%.0f%%", suggestion.confidence * 100))
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Text(suggestion.targetTitle)
                                    .font(.subheadline)
                                    .lineLimit(2)
                                Text(suggestion.reason)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            }
                            .padding(.vertical, 4)
                        }
                        .accessibilityIdentifier("kos.ai.suggestionRow")
                    }
                    .navigationDestination(for: ObjectRoute.self) { route in
                        ObjectDetailView(route: route)
                    }
                }
            }
            .navigationTitle("Suggested Links")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await api.suggestLinks(objectId: object.id)
            suggestions = response.suggestions
        } catch let error as APIError {
            errorMessage = error.userMessage
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
