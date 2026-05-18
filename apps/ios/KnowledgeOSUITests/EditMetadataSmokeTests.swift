import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
/// Opens the first recent object on Home, taps Edit, appends a suffix to the title,
/// saves, reopens the object, and asserts the new title is visible in the nav bar.
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

        // Open the first object from Home. iOS 26 simulator reports List cells as
        // not-hittable for direct .tap(); fall back to a coordinate tap on the
        // cell's frame midpoint (same workaround LoginEndToEndSmokeTests uses for
        // the tab bar).
        let recentList = app.collectionViews.matching(identifier: "kos.home.recentList").firstMatch
        let firstCell = recentList.cells.firstMatch
        XCTAssertTrue(firstCell.waitForExistence(timeout: 20), "Home should have at least one object")
        tapByCoordinate(in: app, frame: firstCell.frame)

        // Wait for object detail and grab the original nav-bar title.
        let editButton = app.navigationBars.buttons["kos.objectDetail.editButton"]
        XCTAssertTrue(editButton.waitForExistence(timeout: 10))
        let originalNavBar = app.navigationBars.element(boundBy: 0)
        let originalTitle = originalNavBar.identifier

        editButton.tap()

        // Append a unique suffix to the title. typeText() appends at the cursor,
        // which lands at the end of the field on focus.
        let titleField = app.textFields["kos.editMetadata.titleField"]
        XCTAssertTrue(titleField.waitForExistence(timeout: 5))
        let suffix = " · edited \(Int(Date().timeIntervalSince1970))"
        titleField.tap()
        titleField.typeText(suffix)
        let expectedTitle = originalTitle + suffix

        app.buttons["kos.editMetadata.saveButton"].tap()

        // 1) In-place check: after save the sheet dismisses and the nav bar shows
        //    the new title without any reload (viewModel.apply(updated:) → @Observable rerender).
        XCTAssertTrue(
            app.navigationBars[expectedTitle].waitForExistence(timeout: 10),
            "Expected nav bar title to update in-place to '\(expectedTitle)'"
        )

        // 2) Persistence check: pop back to Home, re-open the same object,
        //    confirm the title still matches after a fresh GET /objects/{id}.
        let backButton = app.navigationBars.buttons.element(boundBy: 0)
        XCTAssertTrue(backButton.exists)
        backButton.tap()

        let reopenedCell = recentList.cells.firstMatch
        XCTAssertTrue(reopenedCell.waitForExistence(timeout: 10))
        tapByCoordinate(in: app, frame: reopenedCell.frame)

        XCTAssertTrue(
            app.navigationBars[expectedTitle].waitForExistence(timeout: 10),
            "Expected reopened object to still show '\(expectedTitle)' (was '\(originalTitle)')"
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

private func tapByCoordinate(in app: XCUIApplication, frame: CGRect) {
    app.coordinate(withNormalizedOffset: .zero)
        .withOffset(CGVector(dx: frame.midX, dy: frame.midY))
        .tap()
}
