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

                    if let url = viewModel.downloadURL {
                        Link(destination: url) {
                            Label("Download", systemImage: "arrow.down.circle")
                        }
                        .buttonStyle(.borderedProminent)
                    }

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
}
