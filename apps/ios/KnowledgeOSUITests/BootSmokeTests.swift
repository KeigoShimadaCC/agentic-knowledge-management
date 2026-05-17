import XCTest

final class BootSmokeTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLaunchShowsConnectScreen() throws {
        let app = XCUIApplication()
        app.launchArguments += ["-ui-testing-reset"]
        app.launch()

        XCTAssertTrue(app.navigationBars["Connect"].waitForExistence(timeout: 5))
        // Keep in sync with Kos.Connect in AccessibilityID.swift
        XCTAssertTrue(app.textFields["kos.connect.urlField"].exists)
        XCTAssertTrue(app.buttons["kos.connect.testConnectionButton"].exists)
    }
}
