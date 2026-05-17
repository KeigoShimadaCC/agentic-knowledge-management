import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(AuthStore.self) private var authStore
    @State private var selectedTab: MainTab = .home

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeTab()
                .tabItem {
                    Label("Home", systemImage: "house")
                }
                .tag(MainTab.home)

            SearchTab()
                .tabItem {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .tag(MainTab.search)

            CaptureTab()
                .tabItem {
                    Label("Capture", systemImage: "plus.circle")
                }
                .tag(MainTab.capture)

            AITab()
                .tabItem {
                    Label("AI", systemImage: "sparkles")
                }
                .tag(MainTab.ai)

            SettingsTab(onLogout: {
                appState.isSessionAuthenticated = false
                Task { await authStore.logout() }
            })
            .tabItem {
                Label("Settings", systemImage: "gearshape")
            }
            .tag(MainTab.settings)
        }
        .onAppear {
            if let tab = UITestConfig.initialTab {
                selectedTab = tab
            }
        }
    }
}
