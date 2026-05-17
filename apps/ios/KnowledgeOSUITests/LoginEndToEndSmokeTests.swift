import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
final class LoginEndToEndSmokeTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLoginSearchOpenFirstResultFlow() throws {
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

        // Dismiss keyboard if still up after login, then switch to Search tab.
        if app.keyboards.firstMatch.exists {
            app.swipeDown()
        }
        let tabBar = app.tabBars.firstMatch
        XCTAssertTrue(tabBar.waitForExistence(timeout: 10))
        // iOS 26 sim reports tab-bar buttons with hit point {-1,-1} via XCUI label or
        // index lookup. Fall back to tapping at the tab bar's normalized position.
        let tabBarFrame = tabBar.frame
        let searchTabX = tabBarFrame.minX + (tabBarFrame.width * 1.5 / 5.0)
        let searchTabY = tabBarFrame.midY
        app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: searchTabX, dy: searchTabY))
            .tap()

        let search = app.textFields["kos.search.input"]
        XCTAssertTrue(search.waitForExistence(timeout: 15))
        search.tap()
        search.clearAndType("demo")

        let firstResult = app.buttons.matching(identifier: "kos.search.resultRow").firstMatch
        XCTAssertTrue(firstResult.waitForExistence(timeout: 20))
        firstResult.tap()

        XCTAssertFalse(app.navigationBars["Search"].waitForExistence(timeout: 5))

        // Settings tab is the 5th tab — tap via normalized tab-bar coordinate.
        let settingsTabX = tabBarFrame.minX + (tabBarFrame.width * 4.5 / 5.0)
        app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: settingsTabX, dy: searchTabY))
            .tap()
        let toolbarSignOut = app.navigationBars.buttons["kos.settings.logoutButton"]
        if toolbarSignOut.waitForExistence(timeout: 5) {
            toolbarSignOut.tap()
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
