import SwiftUI

struct PendingUploadsView: View {
    let queueStore: any QueueStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.appDependencies) private var dependencies
    @State private var items: [PendingUpload] = []
    @State private var isDraining = false

    var body: some View {
        NavigationStack {
            Group {
                if items.isEmpty {
                    EmptyStateView(
                        title: "Nothing pending",
                        message: "All offline captures have synced."
                    )
                } else {
                    List {
                        ForEach(items, id: \.id) { item in
                            row(for: item)
                        }
                    }
                }
            }
            .navigationTitle("Pending Uploads")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await drainNow() }
                    } label: {
                        if isDraining {
                            ProgressView()
                        } else {
                            Text("Drain now")
                        }
                    }
                    .disabled(items.isEmpty || isDraining)
                    .accessibilityIdentifier("kos.sync.drainNow")
                }
            }
        }
        .task { await refresh() }
    }

    @ViewBuilder
    private func row(for item: PendingUpload) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(label(for: item.kind))
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text("retry \(item.retryCount)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if let error = item.lastError, !error.isEmpty {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .lineLimit(2)
            }
            HStack {
                Text("Next attempt: \(item.nextAttemptAt, style: .relative)")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Cancel", role: .destructive) {
                    Task {
                        try? queueStore.remove(id: item.id)
                        await refresh()
                    }
                }
                .font(.caption)
            }
        }
        .padding(.vertical, 4)
        .accessibilityIdentifier("kos.sync.pendingRow")
    }

    private func label(for kind: PendingUploadKind) -> String {
        switch kind {
        case .quickNote: return "Quick note"
        case let .assetUpload(filename, _, _): return filename
        }
    }

    private func refresh() async {
        items = (try? queueStore.allPending()) ?? []
    }

    private func drainNow() async {
        guard let drainer = dependencies?.queueDrainer else { return }
        isDraining = true
        defer { isDraining = false }
        _ = await drainer.drain()
        await refresh()
    }
}
