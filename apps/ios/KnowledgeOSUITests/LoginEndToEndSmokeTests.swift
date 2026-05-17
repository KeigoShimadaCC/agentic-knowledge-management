import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
final class LoginEndToEndSmokeTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testConnectLoginHomeLogoutFlow() throws {
        let app = XCUIApplication()
        app.launchArguments += ["-ui-testing-reset"]
        app.launch()

        XCTAssertTrue(app.navigationBars["Connect"].waitForExistence(timeout: 8))

        app.buttons["connect.testConnection"].tap()

        // Connect screen is replaced on success — wait for the next screen.
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

        app.tabBars.buttons["Settings"].tap()
        let toolbarSignOut = app.navigationBars.buttons["settings.logout"]
        if toolbarSignOut.waitForExistence(timeout: 5) {
            toolbarSignOut.tap()
        } else {
            app.buttons["ui-test.signout"].tap()
        }

        XCTAssertFalse(app.tabBars.firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(
            app.otherElements["login.screen"].waitForExistence(timeout: 10)
                || app.navigationBars["Sign In"].waitForExistence(timeout: 10)
        )
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
