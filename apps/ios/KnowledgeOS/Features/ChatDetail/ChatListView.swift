import SwiftUI

struct ChatListView: View {
    @State private var viewModel = ChatListViewModel()

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.chats.isEmpty {
                LoadingView(message: "Loading chats...")
            } else if let message = viewModel.errorMessage, viewModel.chats.isEmpty {
                ErrorView(title: "Could not load chats", message: message) {
                    Task { await viewModel.load() }
                }
                .padding()
            } else if viewModel.chats.isEmpty {
                EmptyStateView(
                    title: "No chats",
                    message: "Import chats on your Mac and they will appear here."
                )
                .padding()
            } else {
                List(viewModel.chats) { chat in
                    NavigationLink {
                        ObjectDetailView(route: ObjectRoute(id: chat.id, kind: "chat"))
                    } label: {
                        ChatListRow(chat: chat)
                    }
                    .accessibilityIdentifier(Kos.Chat.row)
                }
                .accessibilityIdentifier(Kos.Chat.list)
                .refreshable {
                    await viewModel.load()
                }
            }
        }
        .navigationTitle("Chats")
        .accessibilityIdentifier(Kos.Chat.listScreen)
        .task {
            await viewModel.load()
        }
    }
}

private struct ChatListRow: View {
    let chat: ObjectDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                ObjectKindBadge(kind: chat.kind)
                Spacer()
                Text(chat.updatedAt, style: .date)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(chat.title)
                .font(.headline)
                .lineLimit(2)

            if let description = chat.description, !description.isEmpty {
                Text(description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}
