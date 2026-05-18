import XCTest
@testable import KnowledgeOS

final class DTOTests: XCTestCase {
    func testMobileLoginResponse() throws {
        let response = try FixtureLoader.decode(MobileLoginResponse.self, named: "mobile_login_response")
        XCTAssertEqual(response.user.email, "mobile@test.com")
        XCTAssertFalse(response.token.isEmpty)
    }

    func testMobileBootstrapResponse() throws {
        let response = try FixtureLoader.decode(MobileBootstrapResponse.self, named: "mobile_bootstrap_response")
        XCTAssertTrue(response.capabilities.uploadEnabled)
        XCTAssertFalse(response.capabilities.embeddingsEnabled)
    }

    func testObjectDTO() throws {
        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        XCTAssertEqual(object.kind, "page")
    }

    func testPaginatedObjects() throws {
        let page = try FixtureLoader.decode(PaginatedResponseDTO<ObjectDTO>.self, named: "paginated_objects")
        XCTAssertEqual(page.items.count, 1)
        XCTAssertEqual(page.page, 1)
    }

    func testPageDTO() throws {
        let page = try FixtureLoader.decode(PageDTO.self, named: "page")
        XCTAssertEqual(page.contentText, "Hello")
        XCTAssertEqual(page.contentJson["type"]?.value as? String, "doc")
    }

    func testHybridSearchResponse() throws {
        let search = try FixtureLoader.decode(HybridSearchResponseDTO.self, named: "hybrid_search")
        XCTAssertEqual(search.results.first?.snippet?.highlights.first?.count, 2)
        XCTAssertFalse(search.embeddingsUsed)
    }

    func testAnswerResponse() throws {
        let answer = try FixtureLoader.decode(AnswerResponseDTO.self, named: "answer")
        XCTAssertEqual(answer.citations.count, 1)
    }

    func testSettingsResponse() throws {
        let settings = try FixtureLoader.decode(SettingsResponseDTO.self, named: "settings")
        XCTAssertEqual(settings.secrets.first?.source, "runtime")
        XCTAssertEqual(settings.features.first?.featureKey, "summarize")
        XCTAssertEqual(settings.prompts.first?.variables, ["content"])
        XCTAssertEqual(settings.mcp.enabledCount, 1)
    }
}
