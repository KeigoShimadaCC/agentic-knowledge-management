import SwiftUI

struct RootView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        NavigationStack {
            Group {
                if appState.isConnected {
                    HomePlaceholderView()
                } else {
                    ConnectView()
                }
            }
            .navigationTitle(appState.isConnected ? "KnowledgeOS" : "Connect")
        }
    }
}

#Preview {
    RootView()
        .environmentObject(AppState(serverConfig: ServerConfig(storage: .init(suiteName: "preview")!)))
}
