import SwiftUI

@MainActor
final class AppDependencies {
    let networkMonitor = NetworkMonitor()
    let apiClient: APIClient
    let authStore: AuthStore

    init() {
        apiClient = APIClient(networkMonitor: networkMonitor)
        authStore = AuthStore(apiClient: apiClient)
        if ProcessInfo.processInfo.arguments.contains("-ui-testing-reset") {
            ServerConfig.shared.reset()
            try? SystemKeychainStore().deleteToken()
        }
    }
}

@main
struct KnowledgeOSApp: App {
    @StateObject private var appState = AppState()
    @State private var dependencies = AppDependencies()

    var body: some Scene {
        WindowGroup {
            RootView(authStore: dependencies.authStore)
                .environmentObject(appState)
                .environment(dependencies.authStore)
                .onAppear {
                    appState.onBaseURLWillChange = { oldURL, newURL in
                        dependencies.authStore.onBaseURLChanged(from: oldURL, to: newURL)
                    }
                }
                .task {
                    await dependencies.authStore.restoreSessionIfNeeded()
                }
        }
    }
}
