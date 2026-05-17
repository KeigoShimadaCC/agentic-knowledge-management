import SwiftUI

struct MainTabView: View {
    @Environment(AuthStore.self) private var authStore

    var body: some View {
        TabView {
            HomeTab()
                .tabItem {
                    Label("Home", systemImage: "house")
                }
                .accessibilityIdentifier("tab.home")

            SearchTab()
                .tabItem {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .accessibilityIdentifier("tab.search")

            CaptureTab()
                .tabItem {
                    Label("Capture", systemImage: "plus.circle")
                }
                .accessibilityIdentifier("tab.capture")

            AITab()
                .tabItem {
                    Label("AI", systemImage: "sparkles")
                }
                .accessibilityIdentifier("tab.ai")

            SettingsTab(onLogout: {
                Task { await authStore.logout() }
            })
            .tabItem {
                Label("Settings", systemImage: "gearshape")
            }
            .accessibilityIdentifier("tab.settings")
        }
        .accessibilityIdentifier("main.tabs")
    }
}
