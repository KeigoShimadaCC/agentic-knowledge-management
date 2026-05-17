import SwiftUI

struct SourceStatusView: View {
    let sourceID: UUID
    @Bindable var viewModel: CaptureViewModel
    @State private var source: SourceDTO?
    @State private var timedOut = false

    var body: some View {
        List {
            Section("Ingestion") {
                HStack {
                    statusIcon
                    VStack(alignment: .leading) {
                        Text(source?.title ?? "Uploaded source")
                            .font(.headline)
                        Text(statusText)
                            .foregroundStyle(.secondary)
                    }
                }

                if timedOut {
                    Button {
                        Task { await refresh() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                }
            }
        }
        .navigationTitle("Upload Status")
        .task(id: sourceID) {
            await poll()
        }
    }

    private var statusText: String {
        if let source {
            return source.ingestionStatus
        }
        return "checking"
    }

    @ViewBuilder
    private var statusIcon: some View {
        switch source?.ingestionStatus {
        case "ready":
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case "failed":
            Image(systemName: "xmark.octagon.fill")
                .foregroundStyle(.red)
        default:
            ProgressView()
        }
    }

    private func poll() async {
        timedOut = false
        for _ in 0..<30 {
            await refresh()
            if source?.ingestionStatus == "ready" || source?.ingestionStatus == "failed" {
                return
            }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
        }
        timedOut = true
    }

    private func refresh() async {
        source = await viewModel.refresh(sourceID: sourceID)
    }
}
