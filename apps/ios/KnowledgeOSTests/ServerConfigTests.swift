import XCTest
@testable import KnowledgeOS

final class ServerConfigTests: XCTestCase {
    func testDefaultBaseURL() {
        let storage = UserDefaults(suiteName: "ServerConfigTests.\(UUID().uuidString)")!
        let config = ServerConfig(storage: storage)

        XCTAssertEqual(config.baseURL.absoluteString, "http://127.0.0.1:8001")
    }

    func testSaveBaseURLStripsTrailingSlash() {
        let storage = UserDefaults(suiteName: "ServerConfigTests.\(UUID().uuidString)")!
        let config = ServerConfig(storage: storage)

        config.saveBaseURL(URL(string: "http://knowledgeos.local:8001/")!)

        XCTAssertEqual(config.baseURL.absoluteString, "http://knowledgeos.local:8001")
    }
}
