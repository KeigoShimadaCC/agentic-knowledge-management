import SwiftUI

struct ObjectDetailView: View {
    let route: ObjectRoute
    @State private var viewModel = ObjectDetailViewModel()
    @State private var isEditingMetadata = false

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
                Button("Edit") {
                    isEditingMetadata = true
                }
                .disabled(viewModel.object == nil)
                .accessibilityIdentifier(Kos.ObjectDetail.editButton)
            }
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
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
    }
}
