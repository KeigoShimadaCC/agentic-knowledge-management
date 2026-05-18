import SwiftUI

struct HomeTab: View {
    @Environment(\.appDependencies) private var dependencies
    @State private var viewModel: HomeViewModel = HomeViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if let queueStore = dependencies?.queueStore {
                    SyncBanner(queueStore: queueStore)
                }
                content
            }
            .navigationTitle("Home")
            .navigationDestination(for: ObjectRoute.self) { route in
                ObjectDetailView(route: route)
            }
            .task {
                if let deps = dependencies {
                    viewModel = HomeViewModel(api: deps.cachedReadAPI)
                }
                await viewModel.loadInitial()
            }
        }
        .accessibilityIdentifier("kos.home.screen")
    }

    @ViewBuilder
    private var content: some View {
        if viewModel.isLoading && viewModel.objects.isEmpty {
            LoadingView(message: "Loading recent objects...")
        } else if let message = viewModel.errorMessage, viewModel.objects.isEmpty {
            ErrorView(title: "Could not load recent objects", message: message) {
                Task { await viewModel.refresh() }
            }
            .padding()
        } else if viewModel.objects.isEmpty {
            EmptyStateView(
                title: "No objects yet",
                message: "Create pages, sources, chats, or projects on your Mac and they will appear here."
            )
        } else {
            List {
                ForEach(viewModel.objects) { object in
                    NavigationLink(value: ObjectRoute(id: object.id, kind: object.kind)) {
                        ObjectRow(object: object)
                    }
                    .task {
                        await viewModel.loadMoreIfNeeded(current: object)
                    }
                }

                if viewModel.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                }
            }
            .accessibilityIdentifier("kos.home.recentList")
            .refreshable {
                await viewModel.refresh()
            }
        }
    }
}

private struct ObjectRow: View {
    let object: ObjectDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                ObjectKindBadge(kind: object.kind)
                Spacer()
                Text(object.updatedAt, style: .date)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(object.title)
                .font(.headline)
                .lineLimit(2)

            if let description = object.description, !description.isEmpty {
                Text(description)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}
