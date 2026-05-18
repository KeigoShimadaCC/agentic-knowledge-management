import SwiftUI

struct PendingUploadsView: View {
    let queueStore: any QueueStore
    @Environment(\.dismiss) private var dismiss
    @Environment(\.appDependencies) private var dependencies
    @State private var items: [PendingUpload] = []
    @State private var isDraining = false

    private var needsAttentionItems: [PendingUpload] {
        items.filter { $0.needsAttention }
    }

    private var retryingItems: [PendingUpload] {
        items.filter { !$0.needsAttention }
    }

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
                        if !needsAttentionItems.isEmpty {
                            Section {
                                ForEach(needsAttentionItems, id: \.id) { item in
                                    needsAttentionRow(for: item)
                                }
                            } header: {
                                Label("Needs attention", systemImage: "exclamationmark.triangle.fill")
                                    .foregroundStyle(.orange)
                                    .accessibilityIdentifier("kos.sync.needsAttentionHeader")
                            } footer: {
                                Text("These captures hit a permanent error (validation, conflict, or auth) and were parked. No retries happen until you act.")
                                    .font(.caption2)
                            }
                        }
                        if !retryingItems.isEmpty {
                            Section("Retrying automatically") {
                                ForEach(retryingItems, id: \.id) { item in
                                    retryingRow(for: item)
                                }
                            }
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
                    .disabled(retryingItems.isEmpty || isDraining)
                    .accessibilityIdentifier("kos.sync.drainNow")
                }
            }
        }
        .task { await refresh() }
    }

    @ViewBuilder
    private func retryingRow(for item: PendingUpload) -> some View {
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

    @ViewBuilder
    private func needsAttentionRow(for item: PendingUpload) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(label(for: item.kind))
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text("permanent error")
                    .font(.caption2)
                    .foregroundStyle(.orange)
            }
            if let error = item.lastError, !error.isEmpty {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .lineLimit(3)
            }
            HStack(spacing: 12) {
                Spacer()
                Button("Try again") {
                    Task {
                        try? queueStore.clearNeedsAttention(id: item.id)
                        await refresh()
                    }
                }
                .font(.caption)
                .accessibilityIdentifier("kos.sync.retryButton")

                Button("Cancel", role: .destructive) {
                    Task {
                        try? queueStore.remove(id: item.id)
                        await refresh()
                    }
                }
                .font(.caption)
                .accessibilityIdentifier("kos.sync.cancelButton")
            }
        }
        .padding(.vertical, 4)
        .accessibilityIdentifier("kos.sync.needsAttentionRow")
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
