import SwiftUI
import UIKit

struct SourceDetailView: View {
    let object: ObjectDTO
    @State private var viewModel = SourceDetailViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                DetailHeader(object: object)
                AIActionsBar(object: object)
                GraphLinksSection(object: object)

                if viewModel.isLoading {
                    LoadingView(message: "Loading source...")
                        .frame(minHeight: 240)
                } else if let message = viewModel.errorMessage {
                    ErrorView(title: "Could not load source", message: message) {
                        Task { await viewModel.load(id: object.id) }
                    }
                } else if let source = viewModel.source {
                    sourceMeta(source)

                    if let image = viewModel.thumbnail {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFit()
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }

                    downloadControl(source)

                    Text(viewModel.text.isEmpty ? source.extractedText ?? "" : viewModel.text)
                        .font(.body)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    EmptyStateView(title: "No source", message: "This source is not available.")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .task {
            await viewModel.load(id: object.id)
        }
    }

    private func sourceMeta(_ source: SourceDTO) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            LabeledContent("Type", value: source.sourceType)
            LabeledContent("Status", value: source.ingestionStatus)
            if let pageCount = source.pageCount {
                LabeledContent("Pages", value: String(pageCount))
            }
        }
        .font(.subheadline)
    }

    @ViewBuilder
    private func downloadControl(_ source: SourceDTO) -> some View {
        if source.assetId == nil {
            EmptyView()
        } else if let url = viewModel.downloadFileURL {
            ShareLink(item: url) {
                Label("Share Download", systemImage: "square.and.arrow.up")
            }
            .buttonStyle(.borderedProminent)
        } else {
            VStack(alignment: .leading, spacing: 6) {
                Button {
                    Task { await viewModel.downloadAssetForSharing() }
                } label: {
                    Label(
                        viewModel.isDownloading ? "Preparing..." : "Download",
                        systemImage: "arrow.down.circle"
                    )
                }
                .buttonStyle(.borderedProminent)
                .disabled(viewModel.isDownloading)

                if let message = viewModel.downloadErrorMessage {
                    Text(message)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }
        }
    }
}
