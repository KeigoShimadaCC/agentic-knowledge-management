import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
final class LoginEndToEndSmokeTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testConnectLoginHomeLogoutFlow() throws {
        let app = XCUIApplication()
        app.launchArguments += ["-ui-testing-reset", "-ui-testing-e2e"]
        app.launch()

        XCTAssertTrue(app.navigationBars["Connect"].waitForExistence(timeout: 8))

        app.buttons["kos.connect.testConnectionButton"].tap()

        let reachedPostConnect =
            app.navigationBars["Sign In"].waitForExistence(timeout: 20)
            || app.tabBars.firstMatch.waitForExistence(timeout: 20)
        XCTAssertTrue(reachedPostConnect)

        let signedIn = app.tabBars.firstMatch.exists
        if !signedIn {
            XCTAssertTrue(app.navigationBars["Sign In"].exists)

            let email = app.textFields["login.email"]
            XCTAssertTrue(email.waitForExistence(timeout: 5))
            email.tap()
            email.clearAndType("demo@example.com")

            let password = app.secureTextFields["login.password"]
            password.tap()
            password.clearAndType("demo-demo-demo")

            app.buttons["login.submit"].tap()
            XCTAssertTrue(app.tabBars.firstMatch.waitForExistence(timeout: 20))
        }

        XCTAssertTrue(app.tabBars.buttons["Home"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["home.username"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.staticTexts["home.username"].label.isEmpty)

        app.terminate()
        sleep(1)

        app.launchArguments = ["-ui-testing-e2e"]
        app.launchEnvironment = ["KOS_UI_LOGOUT": "1"]
        app.launch()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))

        let signedOut =
            app.navigationBars["Sign In"].waitForExistence(timeout: 20)
            || app.textFields["login.email"].waitForExistence(timeout: 20)
        XCTAssertTrue(signedOut, "Expected Sign In after KOS_UI_LOGOUT relaunch")
    }
}

private extension XCUIElement {
    func clearAndType(_ text: String) {
        tap()
        let existing = (value as? String) ?? ""
        if !existing.isEmpty {
            let deleteString = String(repeating: XCUIKeyboardKey.delete.rawValue, count: existing.count)
            typeText(deleteString)
        }
        typeText(text)
    }
}
