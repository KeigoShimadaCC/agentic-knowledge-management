import SwiftUI

struct RootView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Group {
            if !appState.isConnected {
                NavigationStack {
                    ConnectView()
                        .navigationTitle("Connect")
                }
            } else if !appState.isSessionAuthenticated {
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
