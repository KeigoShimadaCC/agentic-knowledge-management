import SwiftUI

struct SummarizeSheet: View {
    let object: ObjectDTO
    var api: AIAPI = AIAPI()

    @Environment(\.dismiss) private var dismiss
    @State private var summary: String?
    @State private var cached: Bool = false
    @State private var isLoading: Bool = true
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(object.title)
                        .font(.headline)
                    if isLoading {
                        ProgressView("Summarizing…")
                            .frame(maxWidth: .infinity, minHeight: 120)
                    } else if let summary {
                        if cached {
                            Text("Cached result")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Text(summary)
                            .font(.body)
                            .accessibilityIdentifier("kos.ai.summaryText")
                    } else if let message = errorMessage {
                        Text(message)
                            .foregroundStyle(.red)
                            .accessibilityIdentifier("kos.ai.summaryError")
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .navigationTitle("Summary")
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
            let response = try await api.summarize(objectId: object.id)
            summary = response.summary
            cached = response.cached
        } catch let error as APIError {
            errorMessage = error.userMessage
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
