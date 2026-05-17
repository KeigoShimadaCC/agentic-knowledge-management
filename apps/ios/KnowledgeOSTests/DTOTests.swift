import XCTest
@testable import KnowledgeOS

final class DTOTests: XCTestCase {
    func testUserDTO() throws {
        let user = try FixtureLoader.decode(UserDTO.self, named: "user")
        XCTAssertEqual(user.email, "mobile@test.com")
        XCTAssertEqual(user.displayName, "Mobile User")
    }

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

    func testIndexStatusDTO() throws {
        let status = try FixtureLoader.decode(IndexStatusDTO.self, named: "index_status")
        XCTAssertEqual(status.status, "done")
        XCTAssertEqual(status.embeddedCount, 4)
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

    func testSourceDTO() throws {
        let source = try FixtureLoader.decode(SourceDTO.self, named: "source")
        XCTAssertEqual(source.sourceType, "web")
        XCTAssertEqual(source.ingestionStatus, "success")
    }

    func testAssetDTO() throws {
        let asset = try FixtureLoader.decode(AssetDTO.self, named: "asset")
        XCTAssertEqual(asset.filename, "photo.jpg")
        XCTAssertEqual(asset.contentType, "image/jpeg")
    }

    func testAssetUploadResponseDTO() throws {
        let upload = try FixtureLoader.decode(AssetUploadResponseDTO.self, named: "asset_upload_response")
        XCTAssertEqual(upload.object.kind, "asset")
        XCTAssertEqual(upload.asset.sha256.count, 64)
    }

    func testChatDTO() throws {
        let chat = try FixtureLoader.decode(ChatDTO.self, named: "chat")
        XCTAssertEqual(chat.turnCount, 2)
        XCTAssertEqual(chat.parsedTurns.first?.role, "user")
    }

    func testProjectDTO() throws {
        let project = try FixtureLoader.decode(ProjectDTO.self, named: "project")
        XCTAssertEqual(project.title, "KnowledgeOS Mobile")
        XCTAssertEqual(project.skills, ["swift", "swiftui"])
    }

    func testWorkspaceDTO() throws {
        let workspace = try FixtureLoader.decode(WorkspaceDTO.self, named: "workspace")
        XCTAssertEqual(workspace.layout.panes.count, 2)
        XCTAssertEqual(workspace.layout.activePaneId, "left")
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

    func testSummarizeResponse() throws {
        let summarize = try FixtureLoader.decode(SummarizeResponseDTO.self, named: "summarize")
        XCTAssertFalse(summarize.summary.isEmpty)
    }

    func testSuggestLinksResponse() throws {
        let links = try FixtureLoader.decode(SuggestLinksResponseDTO.self, named: "suggest_links")
        XCTAssertEqual(links.suggestions.first?.targetKind, "source")
        XCTAssertGreaterThan(links.suggestions.first?.confidence ?? 0, 0.5)
    }
}
