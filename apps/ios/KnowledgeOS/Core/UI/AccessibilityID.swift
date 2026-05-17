import Foundation

/// Central registry of accessibility identifiers for Simulator MCP / UI tests.
/// Convention: `kos.<screen>.<element>` — use these constants in SwiftUI views.
enum Kos {
    enum Connect {
        static let screen = "kos.connect.screen"
        static let urlField = "kos.connect.urlField"
        static let testConnectionButton = "kos.connect.testConnectionButton"
        static let statusIdle = "kos.connect.status.idle"
        static let statusLoading = "kos.connect.status.loading"
        static let statusSuccess = "kos.connect.status.success"
        static let statusFailure = "kos.connect.status.failure"
    }

    enum Login {
        static let screen = "kos.login.screen"
        static let emailField = "kos.login.emailField"
        static let passwordField = "kos.login.passwordField"
        static let submitButton = "kos.login.submitButton"
        static let errorBanner = "kos.login.errorBanner"
    }

    enum Home {
        static let screen = "kos.home.screen"
        static let placeholder = "kos.home.placeholder"
        static let recentList = "kos.home.recentList"
        static let captureButton = "kos.home.captureButton"
    }

    enum Search {
        static let screen = "kos.search.screen"
        static let input = "kos.search.input"
        static let submitButton = "kos.search.submitButton"
        static let resultsList = "kos.search.resultsList"
        static let resultRow = "kos.search.resultRow"
    }

    enum Capture {
        static let screen = "kos.capture.screen"
        static let noteField = "kos.capture.noteField"
        static let saveButton = "kos.capture.saveButton"
    }

    enum Upload {
        static let screen = "kos.upload.screen"
        static let pickButton = "kos.upload.pickButton"
        static let statusLabel = "kos.upload.statusLabel"
    }

    enum AI {
        static let screen = "kos.ai.screen"
        static let questionField = "kos.ai.questionField"
        static let askButton = "kos.ai.askButton"
        static let answerText = "kos.ai.answerText"
    }

    enum Settings {
        static let screen = "kos.settings.screen"
        static let logoutButton = "kos.settings.logoutButton"
    }
}
