import XCTest

enum UITestSession {
    static var sharedSessionBootstrapped = false
}

enum UITestHelpers {
    static let demoEmail = "demo@example.com"
    static let demoPassword = "demo-demo-demo"

    static func launchForUITest(
        app: XCUIApplication,
        reset: Bool = false,
        tab: String? = nil,
        e2e: Bool = true
    ) {
        app.launchArguments = []
        app.launchEnvironment = [:]

        if reset {
            app.launchArguments.append("-ui-testing-reset")
        } else if UITestSession.sharedSessionBootstrapped {
            app.launchArguments.append("-ui-testing-skip-reset")
        }

        if e2e {
            app.launchArguments.append("-ui-testing-e2e")
        }

        if tab != nil {
            app.launchArguments.append("-ui-testing-single-tab")
        }

        if let tab {
            app.launchEnvironment["KOS_UI_TAB"] = tab
            app.launchArguments.append("-KOS_UI_TAB=\(tab)")
        }

        app.launch()
    }

    @discardableResult
    static func signInDemoUser(app: XCUIApplication) -> Bool {
        XCTAssertTrue(app.navigationBars["Connect"].waitForExistence(timeout: 8))

        app.buttons["connect.testConnection"].tap()

        let reachedPostConnect =
            app.navigationBars["Sign In"].waitForExistence(timeout: 20)
            || app.tabBars.firstMatch.waitForExistence(timeout: 20)
        XCTAssertTrue(reachedPostConnect)

        if app.tabBars.firstMatch.exists {
            return true
        }

        XCTAssertTrue(app.navigationBars["Sign In"].exists)

        let email = app.textFields["login.email"]
        XCTAssertTrue(email.waitForExistence(timeout: 5))
        email.tap()
        email.clearAndType(demoEmail)

        let password = app.secureTextFields["login.password"]
        password.tap()
        password.clearAndType(demoPassword)

        app.buttons["login.submit"].tap()
        XCTAssertTrue(app.tabBars.firstMatch.waitForExistence(timeout: 20))
        return true
    }

    static func ensureSignedIn(app: XCUIApplication, reset: Bool = false) {
        if reset || !UITestSession.sharedSessionBootstrapped {
            launchForUITest(app: app, reset: true)
            _ = signInDemoUser(app: app)
            UITestSession.sharedSessionBootstrapped = true
            return
        }

        launchForUITest(app: app, reset: false)
        if app.tabBars.firstMatch.waitForExistence(timeout: 8)
            || app.otherElements.firstMatch.waitForExistence(timeout: 8) {
            return
        }
        _ = signInDemoUser(app: app)
    }

    static func relaunchOnTab(app: XCUIApplication, tab: String) {
        app.terminate()
        launchForUITest(app: app, reset: false, tab: tab)
        if app.tabBars.firstMatch.waitForExistence(timeout: 3) {
            _ = app.wait(for: .runningForeground, timeout: 5)
            switch tab.lowercased() {
            case "search":
                ensureTabSelected("Search", in: app) { searchTabIsActive(in: $0) }
            case "settings":
                ensureTabSelected("Settings", in: app) { settingsTabIsActive(in: $0) }
            case "home":
                ensureTabSelected("Home", in: app) { homeTabIsActive(in: $0) }
            default:
                break
            }
            return
        }

        _ = app.wait(for: .runningForeground, timeout: 5)
        let singleTab = app.otherElements["uitest.singleTab.\(tab.lowercased())"]
        XCTAssertTrue(singleTab.waitForExistence(timeout: 20), "Expected UITest single-tab root for \(tab)")

        switch tab.lowercased() {
        case "search":
            XCTAssertTrue(
                app.textFields["kos.search.input"].waitForExistence(timeout: 20)
            )
        case "settings":
            XCTAssertTrue(waitForSettingsReady(in: app, timeout: 60))
        case "home":
            XCTAssertTrue(UITestHelpers.recentList(in: app).waitForExistence(timeout: 20))
        default:
            break
        }
    }

    static func searchTabIsActive(in app: XCUIApplication) -> Bool {
        if waitForHittable(app.textFields["kos.search.input"], timeout: 1) {
            return true
        }
        return app.navigationBars["Search"].exists
            && app.textFields["kos.search.input"].exists
            && !app.staticTexts["demo@example.com"].exists
    }

    static func settingsTabIsActive(in app: XCUIApplication) -> Bool {
        if waitForHittable(app.buttons["kos.settings.saveKeys"], timeout: 1) {
            return true
        }
        return app.navigationBars["Settings"].exists
            && app.staticTexts["demo@example.com"].exists
            && !app.textFields["kos.search.input"].isHittable
    }

    static func homeTabIsActive(in app: XCUIApplication) -> Bool {
        if firstHittable(in: recentList(in: app).cells) != nil {
            return true
        }
        return app.navigationBars["Home"].exists
            && recentList(in: app).exists
            && !app.staticTexts["demo@example.com"].exists
    }

    /// iOS 26 simulators often ignore `TabView(selection:)` from launch args; tab-bar labels exist but
    /// report hit point `{-1,-1}`. Coordinate tap on the tab button frame is the reliable fallback.
    static func ensureTabSelected(
        _ label: String,
        in app: XCUIApplication,
        isActive: (XCUIApplication) -> Bool,
        timeout: TimeInterval = 20
    ) {
        let tabBar = app.tabBars.firstMatch
        XCTAssertTrue(tabBar.waitForExistence(timeout: timeout))
        let tab = tabBar.buttons[label]
        let tabIndex: Int
        switch label {
        case "Home": tabIndex = 0
        case "Search": tabIndex = 1
        case "Capture": tabIndex = 2
        case "AI": tabIndex = 3
        case "Settings": tabIndex = 4
        default: tabIndex = -1
        }
        if isActive(app) {
            return
        }
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if isActive(app) {
                return
            }
            if tab.exists {
                tapByCoordinate(in: app, frame: tab.frame)
            } else if tabIndex >= 0 {
                let indexed = tabBar.buttons.element(boundBy: tabIndex)
                tapByCoordinate(in: app, frame: indexed.frame)
            }
            RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        }
        XCTAssertTrue(isActive(app), "Expected \(label) tab content to become active")
    }

    static func tapIfNeeded(_ element: XCUIElement, in app: XCUIApplication) {
        XCTAssertTrue(element.waitForExistence(timeout: 10))
        if element.isHittable {
            element.tap()
        } else {
            tapByCoordinate(in: app, frame: element.frame)
        }
    }

    static func recentList(in app: XCUIApplication) -> XCUIElement {
        let table = app.tables.matching(identifier: "kos.home.recentList").firstMatch
        if table.waitForExistence(timeout: 2) {
            return table
        }
        let collection = app.collectionViews.matching(identifier: "kos.home.recentList").firstMatch
        if collection.waitForExistence(timeout: 2) {
            return collection
        }
        return app.otherElements.matching(identifier: "kos.home.recentList").firstMatch
    }

    static func settingsScreen(in app: XCUIApplication) -> Bool {
        waitForSettingsReady(in: app, timeout: 15)
    }

    static func waitForSettingsLoaded(in app: XCUIApplication, timeout: TimeInterval = 60) -> Bool {
        app.descendants(matching: .any)["kos.settings.loaded"].waitForExistence(timeout: timeout)
    }

    static func waitForFeatureEditor(in app: XCUIApplication, timeout: TimeInterval = 10) -> Bool {
        app.descendants(matching: .any)["kos.settings.featureEditor"].waitForExistence(timeout: timeout)
    }

    static func waitForSettingsAPIContent(in app: XCUIApplication, timeout: TimeInterval) -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if app.descendants(matching: .any)["kos.settings.saveKeys"].exists
                || app.descendants(matching: .any)["kos.settings.feature.summarize"].exists
                || app.descendants(matching: .any)["kos.settings.prompt.summarize.page"].exists {
                return true
            }
            app.swipeUp()
            RunLoop.current.run(until: Date().addingTimeInterval(0.4))
        }
        return app.descendants(matching: .any)["kos.settings.saveKeys"].exists
            || app.descendants(matching: .any)["kos.settings.feature.summarize"].exists
    }

    static func returnToSettingsRoot(in app: XCUIApplication) {
        for _ in 0 ..< 6 {
            if app.buttons["kos.settings.workspacesLink"].exists {
                for _ in 0 ..< 3 {
                    app.swipeDown()
                }
                return
            }
            if app.navigationBars.buttons["Settings"].exists {
                tapIfNeeded(app.navigationBars.buttons["Settings"], in: app)
            } else if app.navigationBars.buttons.element(boundBy: 0).exists {
                tapIfNeeded(app.navigationBars.buttons.element(boundBy: 0), in: app)
            }
            RunLoop.current.run(until: Date().addingTimeInterval(0.4))
        }
    }

    static func openSummarizePagePrompt(in app: XCUIApplication) {
        if app.descendants(matching: .any)["kos.settings.prompt.summarize.page"].waitForExistence(timeout: 2) {
            tapSettingsRow(identifier: "kos.settings.prompt.summarize.page", in: app)
            return
        }
        tapSettingsLabel("Summarize Page", in: app)
    }

    static func tapSettingsLabel(_ label: String, in app: XCUIApplication, maxSwipes: Int = 12) {
        for _ in 0 ..< maxSwipes {
            let row = app.staticTexts[label]
            if row.waitForExistence(timeout: 1) {
                tapIfNeeded(row, in: app)
                return
            }
            app.swipeUp()
        }
        XCTFail("Could not find settings label \(label)")
    }

    static func tapSettingsRow(
        identifier: String,
        in app: XCUIApplication,
        maxSwipes: Int = 12
    ) {
        if !app.descendants(matching: .any)[identifier].exists {
            returnToSettingsRoot(in: app)
        }
        for _ in 0 ..< maxSwipes {
            let row = app.descendants(matching: .any)[identifier]
            if row.waitForExistence(timeout: 1) {
                tapIfNeeded(row, in: app)
                return
            }
            app.swipeUp()
        }
        returnToSettingsRoot(in: app)
        for _ in 0 ..< maxSwipes {
            let row = app.descendants(matching: .any)[identifier]
            if row.waitForExistence(timeout: 1) {
                tapIfNeeded(row, in: app)
                return
            }
            app.swipeUp()
        }
        XCTFail("Could not find settings row \(identifier)")
    }

    static func waitForSettingsReady(in app: XCUIApplication, timeout: TimeInterval) -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if app.navigationBars["Settings"].exists,
               app.buttons["kos.settings.workspacesLink"].exists
                || app.staticTexts["demo@example.com"].exists
                || app.buttons["kos.settings.saveKeys"].exists
                || app.navigationBars.buttons["kos.settings.logoutButton"].exists {
                return true
            }
            app.swipeUp()
            RunLoop.current.run(until: Date().addingTimeInterval(0.4))
        }
        return app.navigationBars["Settings"].exists
            && (app.buttons["kos.settings.workspacesLink"].exists
                || app.buttons["kos.settings.saveKeys"].exists)
    }

    static func waitForHittable(_ element: XCUIElement, timeout: TimeInterval) -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if element.exists, element.isHittable {
                return true
            }
            RunLoop.current.run(until: Date().addingTimeInterval(0.25))
        }
        return element.exists && element.isHittable
    }

    static func firstHittable(in query: XCUIElementQuery) -> XCUIElement? {
        for index in 0 ..< query.count {
            let element = query.element(boundBy: index)
            if element.exists, element.isHittable {
                return element
            }
        }
        return nil
    }

    static func hittableElement(
        in app: XCUIApplication,
        identifier: String,
        timeout: TimeInterval = 15
    ) -> XCUIElement? {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if let button = firstHittable(in: app.buttons.matching(identifier: identifier)) {
                return button
            }
            if let cell = firstHittable(in: app.cells.matching(identifier: identifier)) {
                return cell
            }
            if let other = firstHittable(in: app.otherElements.matching(identifier: identifier)) {
                return other
            }
            RunLoop.current.run(until: Date().addingTimeInterval(0.25))
        }
        return nil
    }

    static func tapByCoordinate(in app: XCUIApplication, frame: CGRect) {
        app.coordinate(withNormalizedOffset: .zero)
            .withOffset(CGVector(dx: frame.midX, dy: frame.midY))
            .tap()
    }
}

extension XCUIElement {
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
