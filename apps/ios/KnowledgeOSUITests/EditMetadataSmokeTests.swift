import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
/// Opens the first recent object on Home, taps Edit, appends a suffix to the title,
/// saves, reopens, and asserts the new title is visible in the nav bar.
final class EditMetadataSmokeTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testEditTitleSaveReopenAssertsNewTitle() throws {
        let app = XCUIApplication()
        app.launchArguments += ["-ui-testing-reset"]
        app.launch()

        // Connect → Login (mirrors LoginEndToEndSmokeTests setup).
        XCTAssertTrue(app.navigationBars["Connect"].waitForExistence(timeout: 8))
        app.buttons["connect.testConnection"].tap()

        let reachedPostConnect =
            app.navigationBars["Sign In"].waitForExistence(timeout: 20)
            || app.tabBars.firstMatch.waitForExistence(timeout: 20)
        XCTAssertTrue(reachedPostConnect)

        if !app.tabBars.firstMatch.exists {
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

        if app.keyboards.firstMatch.exists { app.swipeDown() }

        // Open the first object from Home. recentList holds NavigationLinks.
        let recentList = app.collectionViews.matching(identifier: "kos.home.recentList").firstMatch
        let firstCell = recentList.cells.firstMatch
        XCTAssertTrue(firstCell.waitForExistence(timeout: 20), "Home should have at least one object")
        let originalLabel = firstCell.label
        firstCell.tap()

        // Tap nav-bar Edit.
        let editButton = app.navigationBars.buttons["kos.objectDetail.editButton"]
        XCTAssertTrue(editButton.waitForExistence(timeout: 10))
        editButton.tap()

        // Append a unique suffix to the title.
        let titleField = app.textFields["kos.editMetadata.titleField"]
        XCTAssertTrue(titleField.waitForExistence(timeout: 5))
        let suffix = " · edited \(Int(Date().timeIntervalSince1970))"
        titleField.tap()
        titleField.typeText(suffix)

        app.buttons["kos.editMetadata.saveButton"].tap()

        // Sheet dismisses on save. Pop to Home, then re-open to verify persistence.
        let backToHome = app.navigationBars.buttons.firstMatch
        XCTAssertTrue(backToHome.waitForExistence(timeout: 10))
        backToHome.tap()

        let reopened = recentList.cells.firstMatch
        XCTAssertTrue(reopened.waitForExistence(timeout: 10))
        // The updated row label includes the new title.
        XCTAssertTrue(
            reopened.label.contains(suffix.trimmingCharacters(in: .whitespaces)),
            "Expected updated title in row label; got \(reopened.label) (original: \(originalLabel))"
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
