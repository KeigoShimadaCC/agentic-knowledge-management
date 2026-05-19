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

extension Notification.Name {
    static let uitestApplyTab = Notification.Name("kos.uitest.applyTab")
}

enum UITestConfig {
    static var initialTab: MainTab? {
        if let arg = ProcessInfo.processInfo.arguments.first(where: { $0.hasPrefix("-KOS_UI_TAB=") }) {
            let name = String(arg.dropFirst("-KOS_UI_TAB=".count))
            if let tab = MainTab(uiTestName: name) {
                return tab
            }
        }
        if let name = ProcessInfo.processInfo.environment["KOS_UI_TAB"] {
            return MainTab(uiTestName: name)
        }
        return nil
    }

    static var shouldResetOnLaunch: Bool {
        ProcessInfo.processInfo.arguments.contains("-ui-testing-reset")
    }

    static var shouldSkipResetOnLaunch: Bool {
        ProcessInfo.processInfo.arguments.contains("-ui-testing-skip-reset")
    }

    static func postInitialTabIfNeeded() {
        guard let tab = initialTab else { return }
        NotificationCenter.default.post(name: .uitestApplyTab, object: tab)
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
