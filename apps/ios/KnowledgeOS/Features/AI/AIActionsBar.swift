import SwiftUI

struct AIActionsBar: View {
    @Environment(AuthStore.self) private var authStore
    let object: ObjectDTO

    @State private var showingSummary: Bool = false
    @State private var showingSuggestions: Bool = false
    @State private var showingDisabledHint: Bool = false

    private var aiDisabled: Bool {
        authStore.capabilities?.aiEnabled == false
    }

    private var supportsSummarize: Bool {
        object.kind == "page" || object.kind == "source"
    }

    var body: some View {
        HStack(spacing: 8) {
            if supportsSummarize {
                Button {
                    if aiDisabled {
                        showingDisabledHint = true
                    } else {
                        showingSummary = true
                    }
                } label: {
                    Label("Summarize", systemImage: "text.bubble")
                        .labelStyle(.titleAndIcon)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(aiDisabled)
                .accessibilityIdentifier("kos.ai.summarizeButton")
            }

            Button {
                if aiDisabled {
                    showingDisabledHint = true
                } else {
                    showingSuggestions = true
                }
            } label: {
                Label("Suggest Links", systemImage: "link.badge.plus")
                    .labelStyle(.titleAndIcon)
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .disabled(aiDisabled)
            .accessibilityIdentifier("kos.ai.suggestLinksButton")
        }
        .padding(.horizontal)
        .padding(.bottom, 8)
        .opacity(aiDisabled ? 0.55 : 1.0)
        .accessibilityIdentifier("kos.ai.actionsBar")
        .popover(isPresented: $showingDisabledHint) {
            VStack(alignment: .leading, spacing: 8) {
                Text("AI features are disabled on this server.")
                    .font(.subheadline.weight(.semibold))
                Text("Set OPENAI_API_KEY in infra/.env on the host KnowledgeOS server and restart the API to enable.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .frame(maxWidth: 280)
            .presentationCompactAdaptation(.popover)
        }
        .sheet(isPresented: $showingSummary) {
            SummarizeSheet(object: object)
        }
        .sheet(isPresented: $showingSuggestions) {
            SuggestLinksSheet(object: object)
        }
    }
}
