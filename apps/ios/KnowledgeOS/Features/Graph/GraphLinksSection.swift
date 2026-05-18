import SwiftUI

struct GraphLinksSection: View {
    let object: ObjectDTO
    @State private var viewModel = GraphLinksViewModel()
    @State private var showingLinkSheet = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Graph")
                    .font(.headline)
                Spacer()
                Button {
                    showingLinkSheet = true
                } label: {
                    Label("Link", systemImage: "link.badge.plus")
                }
                .buttonStyle(.bordered)
                .accessibilityIdentifier(Kos.Graph.linkButton)
            }

            if viewModel.isLoading {
                ProgressView()
            } else if let message = viewModel.errorMessage, viewModel.outgoing.isEmpty && viewModel.backlinks.isEmpty {
                Text(message)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                GraphEdgeGroup(
                    title: "Outgoing",
                    empty: "No outgoing links.",
                    edges: viewModel.outgoing,
                    objectID: object.id,
                    viewModel: viewModel
                )
                GraphEdgeGroup(
                    title: "Backlinks",
                    empty: "No backlinks.",
                    edges: viewModel.backlinks,
                    objectID: object.id,
                    viewModel: viewModel
                )
            }
        }
        .accessibilityIdentifier(Kos.Graph.section)
        .task {
            await viewModel.load(objectID: object.id)
        }
        .sheet(isPresented: $showingLinkSheet) {
            GraphLinkSheet(object: object, viewModel: viewModel) {
                showingLinkSheet = false
            }
        }
    }
}

private struct GraphEdgeGroup: View {
    let title: String
    let empty: String
    let edges: [EdgeDTO]
    let objectID: UUID
    let viewModel: GraphLinksViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
            if edges.isEmpty {
                Text(empty)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(edges) { edge in
                    GraphEdgeRow(edge: edge, objectID: objectID) {
                        Task { await viewModel.delete(edge, objectID: objectID) }
                    }
                }
            }
        }
    }
}

private struct GraphEdgeRow: View {
    let edge: EdgeDTO
    let objectID: UUID
    let onDelete: () -> Void

    private var other: ObjectSummaryDTO {
        edge.sourceId == objectID ? edge.target : edge.source
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            ObjectKindBadge(kind: other.kind)
            VStack(alignment: .leading, spacing: 4) {
                Text(other.title)
                    .font(.subheadline)
                    .lineLimit(2)
                Text(edge.kind)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button(role: .destructive) {
                onDelete()
            } label: {
                Image(systemName: "xmark.circle")
            }
            .accessibilityLabel("Remove link")
            .accessibilityIdentifier(Kos.Graph.unlinkButton)
        }
        .padding(.vertical, 4)
    }
}

private struct GraphLinkSheet: View {
    let object: ObjectDTO
    let viewModel: GraphLinksViewModel
    let onDone: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var selectedKind = "links_to"
    @State private var selectedTarget: HybridSearchResultDTO?

    private let kinds = ["links_to", "mentions", "supports", "contradicts", "related_to"]

    var body: some View {
        NavigationStack {
            List {
                Section("Target") {
                    TextField("Search objects", text: $query)
                        .textInputAutocapitalization(.never)
                        .accessibilityIdentifier(Kos.Graph.searchField)
                        .onSubmit {
                            Task { await viewModel.searchTargets(query: query, excluding: object.id) }
                        }
                    Button("Search") {
                        Task { await viewModel.searchTargets(query: query, excluding: object.id) }
                    }

                    ForEach(viewModel.searchResults) { result in
                        Button {
                            selectedTarget = result
                        } label: {
                            HStack {
                                ObjectKindBadge(kind: result.kind)
                                Text(result.title)
                                Spacer()
                                if selectedTarget?.id == result.id {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }
                }

                Section("Kind") {
                    Picker("Kind", selection: $selectedKind) {
                        ForEach(kinds, id: \.self) { kind in
                            Text(kind).tag(kind)
                        }
                    }
                    .accessibilityIdentifier(Kos.Graph.kindPicker)
                }
            }
            .navigationTitle("Create Link")
            .accessibilityIdentifier(Kos.Graph.linkSheet)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        guard let selectedTarget else { return }
                        Task {
                            await viewModel.createLink(
                                sourceID: object.id,
                                targetID: selectedTarget.id,
                                kind: selectedKind
                            )
                            onDone()
                        }
                    }
                    .disabled(selectedTarget == nil || viewModel.isMutating)
                    .accessibilityIdentifier(Kos.Graph.createButton)
                }
            }
        }
    }
}
