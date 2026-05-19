import XCTest

/// Live-backend smoke for Settings hub (PHASE-16 parity).
final class SettingsSmokeTests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testSettingsHubPromptFeatureAndMCP() throws {
        UITestHelpers.ensureSignedIn(app: app, reset: !UITestSession.sharedSessionBootstrapped)
        UITestHelpers.relaunchOnTab(app: app, tab: "settings")

        XCTAssertTrue(UITestHelpers.settingsScreen(in: app), "Settings tab should be visible")

        if app.staticTexts["kos.settings.error"].waitForExistence(timeout: 3) {
            XCTFail("Settings load error: \(app.staticTexts["kos.settings.error"].label)")
        }

        XCTAssertTrue(
            UITestHelpers.waitForSettingsAPIContent(in: app, timeout: 60),
            "Settings API content should load (save keys or feature row)"
        )

        UITestHelpers.openSummarizePagePrompt(in: app)

        let editor = app.textViews["kos.settings.promptEditor"]
        if !editor.waitForExistence(timeout: 5) {
            XCTAssertTrue(app.textFields["kos.settings.promptEditor"].waitForExistence(timeout: 5))
        }
        let promptEditor = editor.exists ? editor : app.textFields["kos.settings.promptEditor"]
        promptEditor.tap()
        promptEditor.clearAndType("UITest override: {content}")

        app.swipeUp()
        UITestHelpers.tapSettingsRow(identifier: "kos.settings.promptSave", in: app, maxSwipes: 4)
        _ = app.wait(for: .runningForeground, timeout: 3)

        UITestHelpers.tapSettingsRow(identifier: "kos.settings.promptReset", in: app, maxSwipes: 4)
        _ = app.wait(for: .runningForeground, timeout: 3)

        UITestHelpers.returnToSettingsRoot(in: app)

        // Feature model picker navigation is covered by API tests; reach it here when visible.
        if app.descendants(matching: .any)["kos.settings.feature.summarize"].waitForExistence(timeout: 3) {
            UITestHelpers.tapSettingsRow(identifier: "kos.settings.feature.summarize", in: app)
            app.swipeUp()
            UITestHelpers.tapSettingsRow(identifier: "kos.settings.featureSave", in: app, maxSwipes: 4)
            UITestHelpers.returnToSettingsRoot(in: app)
        }

        let mcpTestButton = app.buttons.matching(
            NSPredicate(format: "identifier BEGINSWITH 'kos.settings.mcp.test.'")
        ).firstMatch
        if mcpTestButton.waitForExistence(timeout: 5) {
            UITestHelpers.tapIfNeeded(mcpTestButton, in: app)
            _ = app.wait(for: .runningForeground, timeout: 5)
        }
    }
}
