import XCTest
@testable import KnowledgeOS

/// Live-backend smoke that exercises the full mobile flow against `docker compose up`
/// **without** depending on XCUITest. iOS 26 simulator + SwiftUI TabView reports tab-bar
/// buttons with hit-point (-1,-1) inside XCUITest, which makes the UI smoke flaky; this
/// drives the same code paths through APIClient + the feature view-models instead.
///
/// Skips automatically when the backend is unreachable so the test is safe to run in CI
/// without docker. To force-enable, set env `KOS_LIVE_SMOKE=1`. Uses the demo login user
/// from compose (`SEED_DEMO_EXAMPLES`) but does not depend on demo search content.
@MainActor
final class LiveBackendSmokeTests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:8001")!
    private let demoEmail = "demo@example.com"
    private let demoPassword = "demo-demo-demo"

    override func setUp() async throws {
        try await super.setUp()
        guard await backendIsReachable() else {
            throw XCTSkip("Backend not reachable at \(baseURL); skipping live smoke.")
        }
    }

    func testLoginSearchAndAskFlowAgainstLiveBackend() async throws {
        let serverConfig = ServerConfig.shared
        serverConfig.saveBaseURL(baseURL)
        let keychain = SmokeInMemoryKeychain()
        let apiClient = APIClient(serverConfig: serverConfig)

        // 1. Login → bearer token.
        let loginBody = MobileLoginRequest(
            email: demoEmail,
            password: demoPassword,
            deviceName: "ios-smoke"
        )
        let login: MobileLoginResponse = try await apiClient.request(
            .mobileLogin,
            body: loginBody,
            auth: false
        )
        XCTAssertFalse(login.token.isEmpty, "Expected a bearer token after mobile-login")
        apiClient.setBearerToken(login.token)
        try keychain.saveToken(login.token)

        // 2. Bootstrap → capabilities.ai_enabled drives the AI-disabled state.
        let bootstrap: MobileBootstrapResponse = try await apiClient.request(
            .mobileBootstrap,
            body: nil as String?,
            auth: true
        )
        XCTAssertEqual(bootstrap.user.email, demoEmail)

        // 3. Self-seed a page, then hybrid-search for its unique marker (no demo seed dependency).
        let marker = UUID().uuidString
        let title = "Live smoke \(marker)"
        let created: PageCreateResponseDTO = try await apiClient.request(
            .createPage,
            body: PageCreateRequest(
                title: title,
                contentJson: TiptapPlainText.tiptapDocument(from: "search marker \(marker)")
            ),
            auth: true
        )
        let search = try await pollHybridSearch(
            apiClient: apiClient,
            query: marker,
            expectedObjectId: created.object.id
        )
        let firstResult = try XCTUnwrap(search.results.first)
        XCTAssertEqual(firstResult.id, created.object.id)

        // 4. Resolve the result via ReadAPI — covers the ObjectDetail dispatcher path.
        let readAPI = ReadAPI(apiClient: apiClient, keychain: keychain)
        let page = try await readAPI.page(id: firstResult.id)
        XCTAssertEqual(page.id, created.page.id)

        // 5. AI answer — only when the backend has AI enabled; otherwise assert disabled mapping.
        let askVM = AskKBViewModel(api: AIAPI(apiClient: apiClient, keychain: keychain))
        askVM.query = "what is \(marker)"
        await askVM.ask()

        if bootstrap.capabilities.aiEnabled {
            XCTAssertNil(askVM.errorMessage, "Live AI answer should succeed when ai_enabled=true")
            let answer = try XCTUnwrap(askVM.answer)
            XCTAssertFalse(answer.answer.isEmpty, "AI answer should be non-empty")
        } else {
            XCTAssertTrue(askVM.aiDisabled, "ai_enabled=false should flip AskKBViewModel.aiDisabled")
            XCTAssertEqual(askVM.errorMessage, APIError.aiDisabled.userMessage)
        }
    }

    // MARK: - Helpers

    private func pollHybridSearch(
        apiClient: APIClient,
        query: String,
        expectedObjectId: UUID,
        maxAttempts: Int = 12,
        delaySeconds: UInt64 = 500_000_000
    ) async throws -> HybridSearchResponseDTO {
        var last: HybridSearchResponseDTO?
        for _ in 0 ..< maxAttempts {
            let response: HybridSearchResponseDTO = try await apiClient.request(
                .hybridSearch,
                body: HybridSearchRequest(
                    q: query,
                    kind: nil,
                    sourceType: nil,
                    limit: 5,
                    debug: false,
                    objectIds: nil
                ),
                auth: true
            )
            last = response
            if response.results.contains(where: { $0.id == expectedObjectId }) {
                return response
            }
            try await Task.sleep(nanoseconds: delaySeconds)
        }
        let count = last?.results.count ?? 0
        XCTFail("Hybrid search never surfaced seeded page after \(maxAttempts) attempts (last hit count: \(count))")
        return try XCTUnwrap(last)
    }

    private func backendIsReachable() async -> Bool {
        if ProcessInfo.processInfo.environment["KOS_LIVE_SMOKE"] == "1" {
            return true
        }
        var request = URLRequest(url: baseURL.appendingPathComponent("/api/v1/health"))
        request.timeoutInterval = 2
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}

private struct SmokeInMemoryKeychain: KeychainStore {
    private final class Storage: @unchecked Sendable {
        let lock = NSLock()
        var token: String?
    }
    private let storage = Storage()

    func readToken() throws -> String? {
        storage.lock.lock(); defer { storage.lock.unlock() }
        return storage.token
    }

    func saveToken(_ token: String) throws {
        storage.lock.lock(); defer { storage.lock.unlock() }
        storage.token = token
    }

    func deleteToken() throws {
        storage.lock.lock(); defer { storage.lock.unlock() }
        storage.token = nil
    }
}
