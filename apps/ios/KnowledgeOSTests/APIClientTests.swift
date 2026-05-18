import XCTest
@testable import KnowledgeOS

final class APIClientTests: XCTestCase {
    override func setUp() {
        super.setUp()
        MockURLProtocol.reset()
    }

    override func tearDown() {
        MockURLProtocol.reset()
        super.tearDown()
    }

    func testAuthenticatedRequestIncludesBearerHeader() async throws {
        let storage = UserDefaults(suiteName: "APIClientTests.\(UUID().uuidString)")!
        storage.set("http://127.0.0.1:8001", forKey: "knowledgeos.baseURL")
        let config = ServerConfig(storage: storage)
        let session = makeMockSession()
        let client = APIClient(serverConfig: config, session: session)
        client.setBearerToken("secret-token")

        MockURLProtocol.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret-token")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, try FixtureLoader.data(named: "mobile_bootstrap_response"))
        }

        let bootstrap: MobileBootstrapResponse = try await client.request(.mobileBootstrap)
        XCTAssertEqual(bootstrap.user.email, "mobile@test.com")
    }

    func testUnauthenticatedRequestOmitsBearerHeader() async throws {
        let storage = UserDefaults(suiteName: "APIClientTests.\(UUID().uuidString)")!
        storage.set("http://127.0.0.1:8001", forKey: "knowledgeos.baseURL")
        let config = ServerConfig(storage: storage)
        let session = makeMockSession()
        let client = APIClient(serverConfig: config, session: session)

        MockURLProtocol.handler = { request in
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, #"{"status":"ok","version":"0.1.0","db":true,"redis":true}"#.data(using: .utf8)!)
        }

        let health = try await client.getHealth()
        XCTAssertEqual(health.status, "ok")
    }

    func test401TriggersUnauthorizedHandler() async throws {
        let storage = UserDefaults(suiteName: "APIClientTests.\(UUID().uuidString)")!
        storage.set("http://127.0.0.1:8001", forKey: "knowledgeos.baseURL")
        let config = ServerConfig(storage: storage)
        let session = makeMockSession()
        let client = APIClient(serverConfig: config, session: session)
        client.setBearerToken("revoked")

        let expectation = expectation(description: "unauthorized")
        client.setUnauthorizedHandler {
            expectation.fulfill()
        }

        MockURLProtocol.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 401,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, try FixtureLoader.data(named: "error_unauthenticated"))
        }

        do {
            let _: MobileBootstrapResponse = try await client.request(.mobileBootstrap)
            XCTFail("Expected unauthorized error")
        } catch let error as APIError {
            XCTAssertEqual(error, .notAuthenticated)
        }

        await fulfillment(of: [expectation], timeout: 1)
    }

    func testMultipartUploadBuildsBoundaryBody() {
        let upload = MultipartUpload(filename: "photo.jpg", mimeType: "image/jpeg", fileData: Data([0xFF, 0xD8]))
        XCTAssertTrue(upload.contentType.contains("multipart/form-data; boundary=\(upload.boundary)"))
        XCTAssertTrue(upload.body.count > 0)
        XCTAssertNotNil(upload.body.range(of: Data("filename=\"photo.jpg\"".utf8)))
        XCTAssertNotNil(upload.body.range(of: Data("--\(upload.boundary)--".utf8)))
    }

    func testPhone08ParityEndpointsUseExpectedPaths() {
        let id = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!

        XCTAssertEqual(APIEndpoint.trashObjects().relativePath, "/api/v1/objects/trash?page=1&limit=25")
        XCTAssertEqual(APIEndpoint.archiveObject(id: id).path, "/api/v1/objects/\(id.uuidString)/archive")
        XCTAssertEqual(APIEndpoint.restoreObject(id: id).path, "/api/v1/objects/\(id.uuidString)/restore")
        XCTAssertEqual(APIEndpoint.workspaces().relativePath, "/api/v1/workspaces?limit=50&offset=0&pinned_only=false")
        XCTAssertEqual(APIEndpoint.workspace(id: id).path, "/api/v1/workspaces/\(id.uuidString)")
        XCTAssertEqual(APIEndpoint.objectEdges(id: id).path, "/api/v1/objects/\(id.uuidString)/edges")
        XCTAssertEqual(APIEndpoint.objectBacklinks(id: id).path, "/api/v1/objects/\(id.uuidString)/backlinks")
        XCTAssertEqual(APIEndpoint.createEdge.path, "/api/v1/edges")
        XCTAssertEqual(APIEndpoint.projects().relativePath, "/api/v1/projects?limit=50&offset=0")
        XCTAssertEqual(APIEndpoint.updateProject(id: id).path, "/api/v1/projects/\(id.uuidString)")
        XCTAssertEqual(APIEndpoint.chatStructuredSummary(id: id).path, "/api/v1/chats/\(id.uuidString)/structured-summary")
        XCTAssertEqual(APIEndpoint.generateChatStructuredSummary(id: id).path, "/api/v1/chats/\(id.uuidString)/structured-summary")
        XCTAssertEqual(APIEndpoint.generateChatStructuredSummary(id: id).method, .post)
        XCTAssertEqual(APIEndpoint.objects(kind: "chat").relativePath, "/api/v1/objects?page=1&limit=25&kind=chat")
    }

    private func makeMockSession() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        return URLSession(configuration: config)
    }
}

private final class MockURLProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    static func reset() {
        handler = nil
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = Self.handler else {
            client?.urlProtocol(self, didFailWithError: URLError(.badURL))
            return
        }
        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
