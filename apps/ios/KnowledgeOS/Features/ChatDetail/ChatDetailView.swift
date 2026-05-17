import SwiftUI

struct ChatDetailView: View {
    let object: ObjectDTO
    @State private var viewModel = ChatDetailViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                DetailHeader(object: object)
                AIActionsBar(object: object)

                if viewModel.isLoading {
                    LoadingView(message: "Loading chat...")
                        .frame(minHeight: 240)
                } else if let message = viewModel.errorMessage {
                    ErrorView(title: "Could not load chat", message: message) {
                        Task { await viewModel.load(id: object.id) }
                    }
                } else if let chat = viewModel.chat {
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
