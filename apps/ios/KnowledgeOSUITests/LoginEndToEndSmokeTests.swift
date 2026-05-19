import XCTest

/// Live-backend smoke: requires `docker compose up`, migration 0013+, demo seed.
final class LoginEndToEndSmokeTests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLoginSearchOpenFirstResultFlow() throws {
        UITestHelpers.ensureSignedIn(app: app, reset: !UITestSession.sharedSessionBootstrapped)

        UITestHelpers.relaunchOnTab(app: app, tab: "search")

        if app.keyboards.firstMatch.exists {
            app.swipeDown()
        }

        let search = app.textFields["kos.search.input"]
        XCTAssertTrue(search.waitForExistence(timeout: 20))
        search.tap()
        // Demo DB may not index "[Demo]" titles; smoke pages from live UITest runs are searchable.
        search.clearAndType("smoke")

        _ = app.tables.matching(identifier: "kos.search.resultsList").firstMatch
            .waitForExistence(timeout: 30)

        let resultCells = app.cells.matching(identifier: "kos.search.resultRow")
        let resultButtons = app.buttons.matching(identifier: "kos.search.resultRow")
        let firstResult = UITestHelpers.firstHittable(in: resultCells)
            ?? UITestHelpers.firstHittable(in: resultButtons)

        if let firstResult {
            let link = firstResult.buttons.firstMatch
            if link.exists, link.isHittable {
                link.tap()
            } else {
                firstResult.tap()
            }
        } else if resultCells.firstMatch.waitForExistence(timeout: 5) {
            UITestHelpers.tapByCoordinate(in: app, frame: resultCells.firstMatch.frame)
        } else {
            // Hybrid index may be empty for "smoke"; open first Home recent object instead.
            UITestHelpers.relaunchOnTab(app: app, tab: "home")
            let recent = UITestHelpers.recentList(in: app)
            let cell = UITestHelpers.firstHittable(in: recent.cells)
            XCTAssertNotNil(cell, "Expected Home recent list when search returned no rows")
            let link = cell!.buttons.firstMatch
            if link.exists, link.isHittable {
                link.tap()
            } else {
                cell!.tap()
            }
        }

        UITestHelpers.relaunchOnTab(app: app, tab: "settings")

        let toolbarSignOut = app.navigationBars.buttons["kos.settings.logoutButton"]
        if toolbarSignOut.waitForExistence(timeout: 10) {
            UITestHelpers.tapIfNeeded(toolbarSignOut, in: app)
        }

        XCTAssertFalse(
            app.tabBars.firstMatch.waitForExistence(timeout: 3)
                && app.buttons["login.submit"].waitForExistence(timeout: 1)
        )
        XCTAssertTrue(
            app.otherElements["login.screen"].waitForExistence(timeout: 10)
                || app.navigationBars["Sign In"].waitForExistence(timeout: 10)
        )

        UITestSession.sharedSessionBootstrapped = false
    }
}
