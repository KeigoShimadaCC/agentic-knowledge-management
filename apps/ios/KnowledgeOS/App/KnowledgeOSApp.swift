import SwiftUI

@main
struct KnowledgeOSApp: App {
    @StateObject private var appState = AppState()
    @State private var authStore: AuthStore
    private let apiClient: APIClient
    private let networkMonitor: NetworkMonitor

    init() {
        let monitor = NetworkMonitor()
        let client = APIClient(networkMonitor: monitor)
        networkMonitor = monitor
        apiClient = client
        _authStore = State(initialValue: AuthStore(apiClient: client))

        if ProcessInfo.processInfo.arguments.contains("-ui-testing-reset") {
            ServerConfig.shared.reset()
            try? SystemKeychainStore().deleteToken()
        }
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
                .environment(authStore)
                .task {
                    authStore.onAuthenticationChange = { authenticated in
                        appState.isSessionAuthenticated = authenticated
                    }
                    appState.isSessionAuthenticated = authStore.isAuthenticated
                    appState.onBaseURLWillChange = { oldURL, newURL in
                        authStore.onBaseURLChanged(from: oldURL, to: newURL)
                    }
                    await authStore.restoreSessionIfNeeded()
                    appState.isSessionAuthenticated = authStore.isAuthenticated

                    if ProcessInfo.processInfo.shouldLogoutOnLaunch, authStore.isAuthenticated {
                        appState.isSessionAuthenticated = false
                        await authStore.logout()
                    }
                }
        }
    }
}
