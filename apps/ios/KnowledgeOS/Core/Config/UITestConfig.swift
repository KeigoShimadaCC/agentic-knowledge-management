import Foundation

enum MainTab: Hashable {
    case home
    case search
    case capture
    case ai
    case settings

    init?(uiTestName: String) {
        switch uiTestName.lowercased() {
        case "home":
            self = .home
        case "search":
            self = .search
        case "capture":
            self = .capture
        case "ai":
            self = .ai
        case "settings":
            self = .settings
        default:
            return nil
        }
    }
}

enum UITestConfig {
    static var initialTab: MainTab? {
        guard let name = ProcessInfo.processInfo.environment["KOS_UI_TAB"] else {
            return nil
        }
        return MainTab(uiTestName: name)
    }
}

extension ProcessInfo {
    var isUITestE2E: Bool {
        arguments.contains("-ui-testing-e2e")
    }

    var shouldLogoutOnLaunch: Bool {
        environment["KOS_UI_LOGOUT"] == "1"
    }
}
