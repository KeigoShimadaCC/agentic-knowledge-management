import XCTest
@testable import KnowledgeOS

@MainActor
final class AppStateTests: XCTestCase {
    func testInitialStateUsesPersistedBaseURL() {
        let storage = UserDefaults(suiteName: "AppStateTests.\(UUID().uuidString)")!
        storage.set("http://example.local:8001", forKey: "knowledgeos.baseURL")

        let appState = AppState(serverConfig: ServerConfig(storage: storage))

        XCTAssertEqual(appState.baseURLString, "http://example.local:8001")
        XCTAssertTrue(appState.isConnected)
    }

    func testMarkConnectedPersistsBaseURL() {
        let storage = UserDefaults(suiteName: "AppStateTests.\(UUID().uuidString)")!
        let appState = AppState(serverConfig: ServerConfig(storage: storage))
        let url = URL(string: "http://127.0.0.1:8001/")!

        appState.markConnected(baseURL: url)

        XCTAssertTrue(appState.isConnected)
        XCTAssertEqual(storage.string(forKey: "knowledgeos.baseURL"), "http://127.0.0.1:8001")
    }

    func testUpdateBaseURLNotifiesWhenNormalizedURLChanges() {
        let storage = UserDefaults(suiteName: "AppStateTests.\(UUID().uuidString)")!
        storage.set("http://127.0.0.1:8001", forKey: "knowledgeos.baseURL")
        let appState = AppState(serverConfig: ServerConfig(storage: storage))
        var captured: (String, String)?
        appState.onBaseURLWillChange = { old, new in
            captured = (old, new)
        }

        appState.updateBaseURL("http://192.168.1.20:8001")

        XCTAssertEqual(captured?.0, "http://127.0.0.1:8001")
        XCTAssertEqual(captured?.1, "http://192.168.1.20:8001")
        XCTAssertFalse(appState.isConnected)
    }
}
