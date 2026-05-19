import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
/// Opens the first recent object on Home, taps Edit, appends a suffix to the title,
/// saves, reopens the object, and asserts the new title is visible in the nav bar.
final class EditMetadataSmokeTests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testEditTitleSaveReopenAssertsNewTitle() throws {
        UITestHelpers.ensureSignedIn(app: app, reset: !UITestSession.sharedSessionBootstrapped)
        UITestHelpers.relaunchOnTab(app: app, tab: "home")

        if app.keyboards.firstMatch.exists {
            app.swipeDown()
        }

        XCTAssertTrue(
            app.otherElements["kos.home.screen"].waitForExistence(timeout: 15)
                || app.navigationBars["Home"].waitForExistence(timeout: 15),
            "Home tab should be visible"
        )

        let recentList = UITestHelpers.recentList(in: app)
        XCTAssertTrue(recentList.waitForExistence(timeout: 20), "Home should show recent list")

        let firstCell = UITestHelpers.firstHittable(in: recentList.cells)
        XCTAssertNotNil(firstCell, "Home should have at least one hittable object")

        let linkButton = firstCell!.buttons.firstMatch
        if linkButton.exists, linkButton.isHittable {
            linkButton.tap()
        } else {
            firstCell!.tap()
        }

        let actionsButton = app.navigationBars.buttons["kos.objectDetail.editButton"]
        XCTAssertTrue(actionsButton.waitForExistence(timeout: 10))
        actionsButton.tap()

        let editMetadata = app.buttons["Edit Metadata"]
        XCTAssertTrue(editMetadata.waitForExistence(timeout: 5))
        editMetadata.tap()

        let titleField = app.textFields["kos.editMetadata.titleField"]
        XCTAssertTrue(titleField.waitForExistence(timeout: 5))
        titleField.tap()
        var originalTitle = (titleField.value as? String) ?? ""
        if originalTitle.isEmpty || originalTitle == "Title" {
            let navTitle = app.navigationBars.element(boundBy: 0).staticTexts.firstMatch.label
            if !navTitle.isEmpty, navTitle != "Back" {
                originalTitle = navTitle
            }
        }
        XCTAssertFalse(originalTitle.isEmpty, "Title field should have a value before edit")

        let suffix = " · edited \(Int(Date().timeIntervalSince1970))"
        titleField.typeText(suffix)

        app.buttons["kos.editMetadata.saveButton"].tap()

        let titleUpdated = app.staticTexts
            .containing(NSPredicate(format: "label CONTAINS %@", suffix))
            .firstMatch
        XCTAssertTrue(titleUpdated.waitForExistence(timeout: 15), "Expected edited title suffix in UI")

        let backButton = app.navigationBars.buttons.element(boundBy: 0)
        XCTAssertTrue(backButton.exists)
        backButton.tap()

        let reopenedCell = recentList.cells.firstMatch
        XCTAssertTrue(reopenedCell.waitForExistence(timeout: 10))
        let reopenedLink = reopenedCell.buttons.firstMatch
        if reopenedLink.exists {
            reopenedLink.tap()
        } else {
            UITestHelpers.tapByCoordinate(in: app, frame: reopenedCell.frame)
        }

        XCTAssertTrue(
            app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", suffix)).firstMatch
                .waitForExistence(timeout: 15),
            "Expected edited title after reopen"
        )
    }
}
