import SwiftUI

struct WorkspaceListView: View {
    @State private var viewModel = WorkspaceListViewModel()

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.workspaces.isEmpty {
                LoadingView(message: "Loading workspaces...")
            } else if let message = viewModel.errorMessage, viewModel.workspaces.isEmpty {
                ErrorView(title: "Could not load workspaces", message: message) {
                    Task { await viewModel.load() }
                }
                .padding()
            } else if viewModel.workspaces.isEmpty {
                EmptyStateView(
                    title: "No workspaces",
                    message: "Create a workspace on your Mac and it will appear here."
                )
                .padding()
            } else {
                List(viewModel.workspaces) { workspace in
                    NavigationLink {
                        WorkspaceDetailView(workspaceID: workspace.id)
                    } label: {
                        WorkspaceRow(workspace: workspace)
                    }
                }
                .accessibilityIdentifier(Kos.Workspace.list)
                .refreshable {
                    await viewModel.load()
                }
            }
        }
        .navigationTitle("Workspaces")
        .accessibilityIdentifier(Kos.Workspace.listScreen)
        .task {
            await viewModel.load()
        }
    }
}

private struct WorkspaceRow: View {
    let workspace: WorkspaceDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(workspace.name)
                    .font(.headline)
                    .lineLimit(2)
                Spacer()
                if workspace.isPinned {
                    Image(systemName: "pin.fill")
                        .foregroundStyle(.secondary)
                }
            }

            if let description = workspace.description, !description.isEmpty {
                Text(description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Text("\(workspace.layout.panes.count) panes")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }
}

struct WorkspaceDetailView: View {
    let workspaceID: UUID
    @State private var viewModel = WorkspaceDetailViewModel()
    @State private var isEditing = false

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.workspace == nil {
                LoadingView(message: "Loading workspace...")
            } else if let message = viewModel.errorMessage, viewModel.workspace == nil {
                ErrorView(title: "Could not load workspace", message: message) {
                    Task { await viewModel.load(id: workspaceID) }
                }
                .padding()
            } else if let workspace = viewModel.workspace {
                WorkspaceDetailContent(workspace: workspace)
            } else {
                EmptyStateView(title: "Workspace not found", message: "This workspace is no longer available.")
                    .padding()
            }
        }
        .navigationTitle(viewModel.workspace?.name ?? "Workspace")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier(Kos.Workspace.detailScreen)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit") {
                    isEditing = true
                }
                .disabled(viewModel.workspace == nil)
                .accessibilityIdentifier(Kos.Workspace.editButton)
            }
        }
        .sheet(isPresented: $isEditing) {
            if let workspace = viewModel.workspace {
                WorkspaceEditSheet(workspace: workspace) { name, description, pinned in
                    await viewModel.update(name: name, description: description, isPinned: pinned)
                    isEditing = false
                }
            }
        }
        .task {
            await viewModel.load(id: workspaceID)
        }
    }
}

private struct WorkspaceDetailContent: View {
    let workspace: WorkspaceDTO

    var body: some View {
        List {
            Section("Details") {
                LabeledContent("Name", value: workspace.name)
                if let description = workspace.description, !description.isEmpty {
                    Text(description)
                }
                LabeledContent("Pinned", value: workspace.isPinned ? "Yes" : "No")
                if let lastUsed = workspace.lastUsedAt {
                    LabeledContent("Last used", value: lastUsed.formatted(date: .abbreviated, time: .shortened))
                }
            }

            Section("Panes") {
                ForEach(workspace.layout.panes, id: \.id) { pane in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(pane.mode.capitalized)
                                .font(.headline)
                            Spacer()
                            Text("\(pane.sizePct)%")
                                .foregroundStyle(.secondary)
                        }
                        if let kind = pane.objectKind {
                            ObjectKindBadge(kind: kind)
                        }
                        if let objectId = pane.objectId {
                            Text(objectId.uuidString)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
    }
}

private struct WorkspaceEditSheet: View {
    let workspace: WorkspaceDTO
    let onSave: (String, String?, Bool) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var name: String
    @State private var description: String
    @State private var isPinned: Bool
    @State private var isSaving = false

    init(workspace: WorkspaceDTO, onSave: @escaping (String, String?, Bool) async -> Void) {
        self.workspace = workspace
        self.onSave = onSave
        _name = State(initialValue: workspace.name)
        _description = State(initialValue: workspace.description ?? "")
        _isPinned = State(initialValue: workspace.isPinned)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Workspace") {
                    TextField("Name", text: $name)
                        .accessibilityIdentifier(Kos.Workspace.nameField)
                    TextField("Description", text: $description, axis: .vertical)
                        .lineLimit(3...5)
                        .accessibilityIdentifier(Kos.Workspace.descriptionField)
                    Toggle("Pinned", isOn: $isPinned)
                        .accessibilityIdentifier(Kos.Workspace.pinnedToggle)
                }
            }
            .navigationTitle("Edit Workspace")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task {
                            isSaving = true
                            await onSave(name, description.isEmpty ? nil : description, isPinned)
                            isSaving = false
                        }
                    } label: {
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Save")
                        }
                    }
                    .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSaving)
                    .accessibilityIdentifier(Kos.Workspace.saveButton)
                }
            }
        }
    }
}
