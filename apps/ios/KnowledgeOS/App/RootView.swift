import SwiftUI

struct RootView: View {
    @EnvironmentObject private var appState: AppState
    @Bindable var authStore: AuthStore

    var body: some View {
        Group {
            if !appState.isConnected {
                NavigationStack {
                    ConnectView()
                        .navigationTitle("Connect")
                }
            } else if !authStore.isAuthenticated {
                NavigationStack {
                    LoginView()
                        .navigationTitle("Sign In")
                }
            } else {
                MainTabView()
            }
        }
    }
}
