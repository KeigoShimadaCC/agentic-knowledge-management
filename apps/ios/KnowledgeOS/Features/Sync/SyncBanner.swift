import SwiftUI

/// Small inline banner shown on Home when there are pending offline uploads.
/// Reads the queue's count via `QueueStore.observe()` so it stays fresh.
struct SyncBanner: View {
    let queueStore: any QueueStore
    @State private var pendingCount: Int = 0
    @State private var showingInspector = false

    var body: some View {
        Group {
            if pendingCount > 0 {
                Button {
                    showingInspector = true
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: "arrow.triangle.2.circlepath")
                        Text("\(pendingCount) pending upload\(pendingCount == 1 ? "" : "s")")
                            .font(.subheadline.weight(.medium))
                        Spacer()
                        Text("Tap to inspect")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(Color.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
                }
                .buttonStyle(.plain)
                .padding(.horizontal)
                .padding(.bottom, 4)
                .accessibilityIdentifier("kos.sync.banner")
            }
        }
        .task {
            for await count in queueStore.observe() {
                pendingCount = count
            }
        }
        .sheet(isPresented: $showingInspector) {
            PendingUploadsView(queueStore: queueStore)
        }
    }
}
