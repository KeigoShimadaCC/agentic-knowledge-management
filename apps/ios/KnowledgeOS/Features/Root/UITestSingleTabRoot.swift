import SwiftUI

/// UITest-only root: renders a single tab without `TabView` so XCUITest can target one screen
/// (iOS 26 keeps off-screen tabs in the accessibility tree, breaking tab-bar automation).
struct UITestSingleTabRoot: View {
    @Environment(AuthStore.self) private var authStore
    let tab: MainTab

    var body: some View {
        Group {
            switch tab {
            case .home:
                HomeTab()
            case .search:
                SearchTab()
            case .capture:
                CaptureTab()
            case .ai:
                AITab()
            case .settings:
                SettingsTab(onLogout: {
                    Task { await authStore.logout() }
                })
            }
        }
        .accessibilityIdentifier("uitest.singleTab.\(tabName)")
    }

    private var tabName: String {
        switch tab {
        case .home: "home"
        case .search: "search"
        case .capture: "capture"
        case .ai: "ai"
        case .settings: "settings"
        }
    }
}

extension UITestConfig {
    static var usesSingleTabRoot: Bool {
        ProcessInfo.processInfo.arguments.contains("-ui-testing-single-tab")
    }
}
