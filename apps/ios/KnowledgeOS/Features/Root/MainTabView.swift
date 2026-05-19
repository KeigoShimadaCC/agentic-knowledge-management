import SwiftUI

struct MainTabView: View {
    @Environment(AuthStore.self) private var authStore
    @State private var selectedTab: MainTab

    init() {
        _selectedTab = State(initialValue: UITestConfig.initialTab ?? .home)
    }

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeTab()
                .tabItem {
                    Label("Home", systemImage: "house")
                }
                .tag(MainTab.home)
                .accessibilityIdentifier("tab.home")

            SearchTab()
                .tabItem {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .tag(MainTab.search)
                .accessibilityIdentifier("tab.search")

            CaptureTab()
                .tabItem {
                    Label("Capture", systemImage: "plus.circle")
                }
                .tag(MainTab.capture)
                .accessibilityIdentifier("tab.capture")

            AITab()
                .tabItem {
                    Label("AI", systemImage: "sparkles")
                }
                .tag(MainTab.ai)
                .accessibilityIdentifier("tab.ai")

            SettingsTab(onLogout: {
                Task { await authStore.logout() }
            })
            .tabItem {
                Label("Settings", systemImage: "gearshape")
            }
            .tag(MainTab.settings)
            .accessibilityIdentifier("tab.settings")
        }
        .accessibilityIdentifier("main.tabs")
        .onAppear {
            applyUITestTabIfNeeded()
        }
        .onChange(of: authStore.isAuthenticated) { _, isAuthenticated in
            if isAuthenticated {
                applyUITestTabIfNeeded()
            }
        }
        .task(id: UITestConfig.initialTab) {
            applyUITestTabIfNeeded()
            if UITestConfig.initialTab != nil {
                try? await Task.sleep(nanoseconds: 300_000_000)
                applyUITestTabIfNeeded()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .uitestApplyTab)) { notification in
            if let tab = notification.object as? MainTab {
                selectedTab = tab
            }
        }
    }

    private func applyUITestTabIfNeeded() {
        if let tab = UITestConfig.initialTab {
            selectedTab = tab
        }
    }
}
