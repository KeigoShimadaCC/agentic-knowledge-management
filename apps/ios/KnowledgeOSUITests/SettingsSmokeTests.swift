import XCTest

/// Live-backend smoke for Settings hub (PHASE-16 parity).
final class SettingsSmokeTests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testSettingsHubPromptAndMCP() throws {
        UITestHelpers.ensureSignedIn(app: app, reset: !UITestSession.sharedSessionBootstrapped)
        UITestHelpers.relaunchOnTab(app: app, tab: "settings")

        XCTAssertTrue(UITestHelpers.settingsScreen(in: app), "Settings tab should be visible")

        if app.staticTexts["kos.settings.error"].waitForExistence(timeout: 3) {
            XCTFail("Settings load error: \(app.staticTexts["kos.settings.error"].label)")
        }

        XCTAssertTrue(
            UITestHelpers.waitForSettingsLoaded(in: app, timeout: 60),
            "Settings API content should load"
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

        let mcpTestButton = app.buttons.matching(
            NSPredicate(format: "identifier BEGINSWITH 'kos.settings.mcp.test.'")
        ).firstMatch
        if mcpTestButton.waitForExistence(timeout: 5) {
            UITestHelpers.tapIfNeeded(mcpTestButton, in: app)
            _ = app.wait(for: .runningForeground, timeout: 5)
        }
    }

    func testSettingsFeatureModelSave() throws {
        UITestHelpers.ensureSignedIn(app: app, reset: !UITestSession.sharedSessionBootstrapped)
        UITestHelpers.relaunchOnTab(app: app, tab: "settings")

        XCTAssertTrue(UITestHelpers.waitForSettingsLoaded(in: app, timeout: 60))

        guard app.descendants(matching: .any)["kos.settings.feature.summarize"].waitForExistence(timeout: 5) else {
            throw XCTSkip("Summarize feature row not visible on this backend profile")
        }

        UITestHelpers.tapSettingsRow(identifier: "kos.settings.feature.summarize", in: app)
        XCTAssertTrue(UITestHelpers.waitForFeatureEditor(in: app), "Feature editor should open")

        let modelField = app.textFields["kos.settings.featureModel"]
        XCTAssertTrue(modelField.waitForExistence(timeout: 5))
        modelField.tap()
        modelField.clearAndType("gpt-4o-mini-uitest")

        UITestHelpers.tapSettingsRow(identifier: "kos.settings.featureSave", in: app, maxSwipes: 4)
        _ = app.wait(for: .runningForeground, timeout: 3)

        UITestHelpers.returnToSettingsRoot(in: app)
        XCTAssertTrue(
            app.descendants(matching: .any)["kos.settings.workspacesLink"].waitForExistence(timeout: 10),
            "Should return to settings root after feature save"
        )
    }
}
