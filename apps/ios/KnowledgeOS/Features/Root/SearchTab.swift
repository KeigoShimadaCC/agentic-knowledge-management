import SwiftUI

struct SearchTab: View {
    @State private var viewModel = SearchViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                TextField("Search KnowledgeOS", text: $viewModel.query)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textFieldStyle(.roundedBorder)
                    .padding()
                    .accessibilityIdentifier("kos.search.input")
                    .onChange(of: viewModel.query) { _, newValue in
                        viewModel.scheduleSearch(for: newValue)
                    }

                Group {
                    if viewModel.isLoading && viewModel.results.isEmpty {
                        LoadingView(message: "Searching...")
                    } else if let message = viewModel.errorMessage {
                        ErrorView(title: "Search failed", message: message) {
                            Task { await viewModel.searchNow() }
                        }
                        .padding()
                        Spacer()
                    } else if viewModel.query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        EmptyStateView(title: "Search", message: "Search pages, sources, chats, and projects.")
                    } else if viewModel.results.isEmpty {
                        EmptyStateView(title: "No results", message: "Try another keyword.")
                    } else {
                        List(viewModel.results) { result in
                            NavigationLink(value: ObjectRoute(id: result.id, kind: result.kind)) {
                                SearchResultRow(result: result)
                            }
                            .accessibilityIdentifier("kos.search.resultRow")
                        }
                        .accessibilityIdentifier("kos.search.resultsList")
                    }
                }
            }
            .navigationTitle("Search")
            .navigationDestination(for: ObjectRoute.self) { route in
                ObjectDetailView(route: route)
            }
        }
        .accessibilityIdentifier("kos.search.screen")
    }
}

private struct SearchResultRow: View {
    let result: HybridSearchResultDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                ObjectKindBadge(kind: result.kind)
                Spacer()
                Text(result.updatedAt, style: .date)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(result.title)
                .font(.headline)
                .lineLimit(2)

            if let snippet = result.snippet?.text, !snippet.isEmpty {
                Text(snippet)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }
        }
        .padding(.vertical, 4)
    }
}
