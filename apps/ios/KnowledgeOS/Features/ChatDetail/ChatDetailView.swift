import SwiftUI

struct ChatDetailView: View {
    let object: ObjectDTO
    @State private var viewModel = ChatDetailViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                DetailHeader(object: object)
                AIActionsBar(object: object)
                GraphLinksSection(object: object)

                if viewModel.isLoading {
                    LoadingView(message: "Loading chat...")
                        .frame(minHeight: 240)
                } else if let message = viewModel.errorMessage {
                    ErrorView(title: "Could not load chat", message: message) {
                        Task { await viewModel.load(id: object.id) }
                    }
                } else if let chat = viewModel.chat {
                    ChatSummaryReviewSection(
                        chat: chat,
                        preview: viewModel.summaryPreview,
                        isLoading: viewModel.isSummaryLoading,
                        errorMessage: viewModel.summaryErrorMessage,
                        onLoad: { Task { await viewModel.loadSummary(id: chat.id) } },
                        onGenerate: { Task { await viewModel.generateSummary(id: chat.id) } }
                    )
                    ForEach(Array(chat.parsedTurns.enumerated()), id: \.offset) { _, turn in
                        ChatTurnCard(turn: turn)
                    }
                } else {
                    EmptyStateView(title: "No chat", message: "This chat has no turns.")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .task {
            await viewModel.load(id: object.id)
        }
    }
}

private struct ChatSummaryReviewSection: View {
    let chat: ChatDTO
    let preview: StructuredSummaryPreviewDTO?
    let isLoading: Bool
    let errorMessage: String?
    let onLoad: () -> Void
    let onGenerate: () -> Void

    private var hasStoredSummary: Bool {
        chat.structuredSummary != nil || chat.structuredSummaryStatus == "previewed" || chat.structuredSummaryStatus == "applied"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text("Structured Summary")
                    .font(.headline)
                Spacer()
                Text(preview?.status ?? chat.structuredSummaryStatus)
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(.blue.opacity(0.12), in: Capsule())
                    .accessibilityIdentifier("kos.chat.summary.status")
            }

            if let preview {
                StructuredSummaryPreviewContent(preview: preview)
            } else {
                Text(hasStoredSummary ? "Summary metadata is available." : "No structured summary preview loaded.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .accessibilityIdentifier("kos.chat.summary.empty")
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .accessibilityIdentifier("kos.chat.summary.error")
            }

            HStack {
                Button {
                    onLoad()
                } label: {
                    Label("Load Summary", systemImage: "doc.text.magnifyingglass")
                }
                .buttonStyle(.bordered)
                .disabled(isLoading)
                .accessibilityIdentifier("kos.chat.summary.load")

                Button {
                    onGenerate()
                } label: {
                    Label("Generate Preview", systemImage: "sparkles")
                }
                .buttonStyle(.borderedProminent)
                .disabled(isLoading)
                .accessibilityIdentifier("kos.chat.summary.generate")
            }

            if isLoading {
                ProgressView()
                    .accessibilityIdentifier("kos.chat.summary.loading")
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.blue.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
        .accessibilityIdentifier("kos.chat.summary.review")
    }
}

private struct StructuredSummaryPreviewContent: View {
    let preview: StructuredSummaryPreviewDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(preview.structuredSummary.title)
                .font(.subheadline.weight(.semibold))
                .accessibilityIdentifier("kos.chat.summary.title")
            Text(preview.structuredSummary.summary)
                .font(.subheadline)
                .textSelection(.enabled)
                .accessibilityIdentifier("kos.chat.summary.body")

            SummaryChips(title: "Topics", items: preview.structuredSummary.topics)
            SummaryBullets(title: "Key Decisions", items: preview.structuredSummary.keyDecisions.map(\.decision))
            SummaryBullets(title: "Action Items", items: preview.structuredSummary.actionItems.map(\.task))
            SummaryBullets(title: "Open Questions", items: preview.structuredSummary.openQuestions.map(\.question))
            SummaryBullets(title: "Claims", items: preview.structuredSummary.claims.map(\.claim))
            SummaryBullets(title: "Concepts", items: preview.structuredSummary.concepts.map(\.name))
            SummaryBullets(title: "Suggested Links", items: preview.structuredSummary.suggestedLinks.map { "\($0.targetTitle) - \($0.edgeKind)" })
            SummaryBullets(title: "Warnings", items: preview.structuredSummary.warnings)
        }
    }
}

private struct SummaryChips: View {
    let title: String
    let items: [String]

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(items, id: \.self) { item in
                            Text(item)
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.gray.opacity(0.15), in: Capsule())
                        }
                    }
                }
            }
        }
    }
}

private struct SummaryBullets: View {
    let title: String
    let items: [String]

    var body: some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                    Text("- \(item)")
                        .font(.caption)
                        .textSelection(.enabled)
                }
            }
        }
    }
}

private struct ChatTurnCard: View {
    let turn: ChatTurnDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(turn.role.capitalized)
                    .font(.caption.weight(.semibold))
                if let author = turn.author, !author.isEmpty {
                    Text(author)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Text(turn.content)
                .textSelection(.enabled)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.gray.opacity(0.1), in: RoundedRectangle(cornerRadius: 8))
    }
}
