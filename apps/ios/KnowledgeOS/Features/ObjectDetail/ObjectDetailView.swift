import SwiftUI

struct ObjectDetailView: View {
    let route: ObjectRoute
    @State private var viewModel = ObjectDetailViewModel()
    @State private var isEditingMetadata = false
    @State private var showLifecycleConfirmation = false

    var body: some View {
        Group {
            if viewModel.isLoading {
                LoadingView(message: "Loading object...")
            } else if let message = viewModel.errorMessage {
                ErrorView(title: "Could not open object", message: message) {
                    Task { await viewModel.load(id: route.id) }
                }
                .padding()
            } else if let object = viewModel.object {
                switch object.kind {
                case "page":
                    PageDetailView(object: object)
                case "source":
                    SourceDetailView(object: object)
                case "chat":
                    ChatDetailView(object: object)
                case "project":
                    ProjectDetailView(object: object)
                default:
                    UnsupportedObjectView(object: object)
                }
            } else {
                EmptyStateView(title: "Object not found", message: "This object is no longer available.")
            }
        }
        .navigationTitle(viewModel.object?.title ?? "Object")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button {
                        isEditingMetadata = true
                    } label: {
                        Label("Edit Metadata", systemImage: "pencil")
                    }
                    .disabled(viewModel.object == nil || viewModel.isMutating)

                    Button {
                        Task { await viewModel.archiveCurrentObject() }
                    } label: {
                        Label("Archive", systemImage: "archivebox")
                    }
                    .disabled(viewModel.object == nil || viewModel.object?.isArchived == true || viewModel.isMutating)

                    Button(role: .destructive) {
                        showLifecycleConfirmation = true
                    } label: {
                        Label("Move to Trash", systemImage: "trash")
                    }
                    .disabled(viewModel.object == nil || viewModel.object?.deletedAt != nil || viewModel.isMutating)
                } label: {
                    if viewModel.isMutating {
                        ProgressView()
                    } else {
                        Label("Object actions", systemImage: "ellipsis.circle")
                    }
                }
                .disabled(viewModel.object == nil)
                .accessibilityIdentifier(Kos.ObjectDetail.editButton)
            }
        }
        .confirmationDialog(
            "Move this object to trash?",
            isPresented: $showLifecycleConfirmation,
            titleVisibility: .visible
        ) {
            Button("Move to Trash", role: .destructive) {
                Task { await viewModel.moveCurrentObjectToTrash() }
            }
            Button("Cancel", role: .cancel) {}
        }
        .sheet(isPresented: $isEditingMetadata) {
            if let object = viewModel.object {
                EditMetadataSheet(object: object) { updated in
                    viewModel.apply(updated: updated)
                }
            }
        }
        .task {
            await viewModel.load(id: route.id)
        }
    }
}

private struct UnsupportedObjectView: View {
    let object: ObjectDTO

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                ObjectKindBadge(kind: object.kind)
                Text(object.title)
                    .font(.title2.weight(.semibold))
                Text("Unsupported object kind.")
                    .foregroundStyle(.secondary)
                AIActionsBar(object: object)
                GraphLinksSection(object: object)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
    }
}
