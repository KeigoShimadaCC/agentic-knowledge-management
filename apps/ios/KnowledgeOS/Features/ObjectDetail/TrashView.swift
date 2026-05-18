import SwiftUI

struct TrashView: View {
    @State private var viewModel = TrashViewModel()

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.objects.isEmpty {
                LoadingView(message: "Loading trash...")
            } else if let message = viewModel.errorMessage, viewModel.objects.isEmpty {
                ErrorView(title: "Could not load trash", message: message) {
                    Task { await viewModel.load() }
                }
                .padding()
            } else if viewModel.objects.isEmpty {
                EmptyStateView(title: "Trash is empty", message: "Deleted objects from Mac or iPhone will appear here.")
                    .padding()
            } else {
                List(viewModel.objects) { object in
                    TrashObjectRow(
                        object: object,
                        isRestoring: viewModel.isRestoring == object.id
                    ) {
                        Task { await viewModel.restore(object) }
                    }
                }
                .accessibilityIdentifier(Kos.Trash.list)
                .refreshable {
                    await viewModel.load()
                }
            }
        }
        .navigationTitle("Trash")
        .accessibilityIdentifier(Kos.Trash.screen)
        .task {
            await viewModel.load()
        }
    }
}

private struct TrashObjectRow: View {
    let object: ObjectDTO
    let isRestoring: Bool
    let onRestore: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                ObjectKindBadge(kind: object.kind)
                Spacer()
                if let deletedAt = object.deletedAt {
                    Text(deletedAt, style: .date)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Text(object.title)
                .font(.headline)
                .lineLimit(2)

            Button {
                onRestore()
            } label: {
                if isRestoring {
                    ProgressView()
                } else {
                    Label("Restore", systemImage: "arrow.uturn.backward")
                }
            }
            .disabled(isRestoring)
            .accessibilityIdentifier(Kos.Trash.restoreButton)
        }
        .padding(.vertical, 4)
    }
}
