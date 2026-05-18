import SwiftUI

struct ProjectDetailView: View {
    let object: ObjectDTO
    @State private var viewModel = ProjectDetailViewModel()
    @State private var isEditing = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                DetailHeader(object: object)
                AIActionsBar(object: object)
                GraphLinksSection(object: object)

                if viewModel.isLoading {
                    LoadingView(message: "Loading project...")
                        .frame(minHeight: 240)
                } else if let message = viewModel.errorMessage {
                    ErrorView(title: "Could not load project", message: message) {
                        Task { await viewModel.load(id: object.id) }
                    }
                } else if let project = viewModel.project {
                    ProjectFields(project: project)
                    LinkedObjectsSection(related: viewModel.related)
                } else {
                    EmptyStateView(title: "No project", message: "This project is not available.")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .task {
            await viewModel.load(id: object.id)
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    isEditing = true
                } label: {
                    Label("Edit Project", systemImage: "square.and.pencil")
                }
                .disabled(viewModel.project == nil || viewModel.isSaving)
                .accessibilityIdentifier(Kos.Project.editButton)
            }
        }
        .sheet(isPresented: $isEditing) {
            if let project = viewModel.project {
                ProjectEditSheet(project: project) { title, description, role, organization, status, skills in
                    await viewModel.update(
                        title: title,
                        description: description,
                        role: role,
                        organization: organization,
                        status: status,
                        skills: skills
                    )
                    isEditing = false
                }
            }
        }
    }
}

private struct ProjectFields: View {
    let project: ProjectDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let role = project.role { LabeledContent("Role", value: role) }
            if let organization = project.organization { LabeledContent("Organization", value: organization) }
            LabeledContent("Status", value: project.status)
            if !project.skills.isEmpty {
                Text(project.skills.joined(separator: ", "))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            LongField(title: "Problem", value: project.problem)
            LongField(title: "Actions", value: project.actions)
            LongField(title: "Results", value: project.results)
        }
    }
}

private struct LongField: View {
    let title: String
    let value: String?

    var body: some View {
        if let value, !value.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.headline)
                Text(value).textSelection(.enabled)
            }
        }
    }
}

private struct LinkedObjectsSection: View {
    let related: [RelatedObjectDTO]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Linked Objects")
                .font(.headline)

            if related.isEmpty {
                Text("No linked objects yet.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(related) { item in
                    HStack {
                        ObjectKindBadge(kind: item.object.kind)
                        Text(item.object.title)
                            .lineLimit(2)
                    }
                }
            }
        }
    }
}

private struct ProjectEditSheet: View {
    let project: ProjectDTO
    let onSave: (String, String?, String?, String?, String, [String]) async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var title: String
    @State private var description: String
    @State private var role: String
    @State private var organization: String
    @State private var status: String
    @State private var skillsText: String
    @State private var isSaving = false

    private let statuses = ["active", "paused", "completed", "archived"]

    init(
        project: ProjectDTO,
        onSave: @escaping (String, String?, String?, String?, String, [String]) async -> Void
    ) {
        self.project = project
        self.onSave = onSave
        _title = State(initialValue: project.title)
        _description = State(initialValue: project.description ?? "")
        _role = State(initialValue: project.role ?? "")
        _organization = State(initialValue: project.organization ?? "")
        _status = State(initialValue: project.status)
        _skillsText = State(initialValue: project.skills.joined(separator: ", "))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Project") {
                    TextField("Title", text: $title)
                        .accessibilityIdentifier(Kos.Project.titleField)
                    TextField("Description", text: $description, axis: .vertical)
                        .lineLimit(3...5)
                    TextField("Role", text: $role)
                    TextField("Organization", text: $organization)
                    Picker("Status", selection: $status) {
                        ForEach(statuses, id: \.self) { status in
                            Text(status.capitalized).tag(status)
                        }
                    }
                    .accessibilityIdentifier(Kos.Project.statusPicker)
                    TextField("Skills", text: $skillsText, axis: .vertical)
                        .lineLimit(2...4)
                }
            }
            .navigationTitle("Edit Project")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task {
                            isSaving = true
                            await onSave(
                                title,
                                description.emptyToNil,
                                role.emptyToNil,
                                organization.emptyToNil,
                                status,
                                skillsText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
                            )
                            isSaving = false
                        }
                    } label: {
                        if isSaving {
                            ProgressView()
                        } else {
                            Text("Save")
                        }
                    }
                    .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSaving)
                    .accessibilityIdentifier(Kos.Project.saveButton)
                }
            }
        }
    }
}

private extension String {
    var emptyToNil: String? {
        let trimmed = trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}
