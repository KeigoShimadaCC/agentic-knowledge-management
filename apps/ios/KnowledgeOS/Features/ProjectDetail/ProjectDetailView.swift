import SwiftUI

struct ProjectDetailView: View {
    let object: ObjectDTO
    @State private var viewModel = ProjectDetailViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                DetailHeader(object: object)
                AIActionsBar(object: object)

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
