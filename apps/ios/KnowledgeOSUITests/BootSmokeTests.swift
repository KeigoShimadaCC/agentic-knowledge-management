import XCTest

final class BootSmokeTests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testLaunchShowsConnectScreen() throws {
        let app = XCUIApplication()
        app.launch()

        XCTAssertTrue(app.navigationBars["Connect"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.textFields["connect.baseURL"].exists)
        XCTAssertTrue(app.buttons["connect.testConnection"].exists)
    }
}
