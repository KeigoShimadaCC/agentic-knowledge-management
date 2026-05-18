import SwiftUI

struct ProjectListView: View {
    @State private var viewModel = ProjectListViewModel()

    var body: some View {
        Group {
            if viewModel.isLoading && viewModel.projects.isEmpty {
                LoadingView(message: "Loading projects...")
            } else if let message = viewModel.errorMessage, viewModel.projects.isEmpty {
                ErrorView(title: "Could not load projects", message: message) {
                    Task { await viewModel.load() }
                }
                .padding()
            } else if viewModel.projects.isEmpty {
                EmptyStateView(title: "No projects", message: "Create a project on your Mac and it will appear here.")
                    .padding()
            } else {
                List(viewModel.projects) { project in
                    NavigationLink {
                        ObjectDetailView(route: ObjectRoute(id: project.id, kind: "project"))
                    } label: {
                        ProjectListRow(project: project)
                    }
                }
                .accessibilityIdentifier(Kos.Project.list)
                .refreshable {
                    await viewModel.load()
                }
            }
        }
        .navigationTitle("Projects")
        .accessibilityIdentifier(Kos.Project.listScreen)
        .task {
            await viewModel.load()
        }
    }
}

private struct ProjectListRow: View {
    let project: ProjectDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(project.title)
                    .font(.headline)
                    .lineLimit(2)
                Spacer()
                Text(project.status.capitalized)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            if let organization = project.organization, !organization.isEmpty {
                Text(organization)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            if !project.skills.isEmpty {
                Text(project.skills.prefix(4).joined(separator: ", "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
        .padding(.vertical, 4)
    }
}
