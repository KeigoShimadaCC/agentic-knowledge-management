import SwiftUI

struct CaptureTab: View {
    @Environment(AuthStore.self) private var authStore
    @Environment(\.appDependencies) private var dependencies
    @State private var viewModel: CaptureViewModel?

    var body: some View {
        NavigationStack {
            if let viewModel {
                CaptureRootView(viewModel: viewModel)
            } else {
                LoadingView(message: "Preparing Capture")
                    .navigationTitle("Capture")
            }
        }
        .accessibilityIdentifier(Kos.Capture.entry)
        .task {
            if viewModel == nil {
                viewModel = CaptureViewModel(
                    api: KnowledgeOSCaptureAPI(apiClient: authStore.apiClient),
                    queueStore: dependencies?.queueStore
                )
            }
        }
    }
}
