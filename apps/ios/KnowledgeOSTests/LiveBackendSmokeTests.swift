import XCTest
@testable import KnowledgeOS

/// Live-backend smoke that exercises the full mobile flow against `docker compose up`
/// **without** depending on XCUITest. iOS 26 simulator + SwiftUI TabView reports tab-bar
/// buttons with hit-point (-1,-1) inside XCUITest, which makes the UI smoke flaky; this
/// drives the same code paths through APIClient + the feature view-models instead.
///
/// Skips automatically when the backend is unreachable so the test is safe to run in CI
/// without docker. To force-enable, set env `KOS_LIVE_SMOKE=1`. The demo user must exist
/// (created by `services/api/scripts/seed_demo.py`).
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

        // 3. Hybrid search returns the demo seed.
        let search: HybridSearchResponseDTO = try await apiClient.request(
            .hybridSearch,
            body: HybridSearchRequest(
                q: "demo",
                kind: nil,
                sourceType: nil,
                limit: 5,
                debug: false,
                objectIds: nil
            ),
            auth: true
        )
        XCTAssertGreaterThan(search.results.count, 0, "Demo seed should produce search hits for 'demo'")
        let firstResult = try XCTUnwrap(search.results.first)

        // 4. Resolve the first result via ReadAPI — covers the ObjectDetail dispatcher path.
        let readAPI = ReadAPI(apiClient: apiClient, keychain: keychain)
        switch firstResult.kind {
        case "page":
            let page = try await readAPI.page(id: firstResult.id)
            XCTAssertEqual(page.id, firstResult.id)
        case "source":
            let source = try await readAPI.source(id: firstResult.id)
            XCTAssertEqual(source.id, firstResult.id)
        default:
            let object = try await readAPI.object(id: firstResult.id)
            XCTAssertEqual(object.id, firstResult.id)
        }

        // 5. AI answer — only when the backend has AI enabled; otherwise assert disabled mapping.
        let askVM = AskKBViewModel(api: AIAPI(apiClient: apiClient, keychain: keychain))
        askVM.query = "what is knowledgeos"
        await askVM.ask()

        if bootstrap.capabilities.aiEnabled {
            XCTAssertNil(askVM.errorMessage, "Live AI answer should succeed when ai_enabled=true")
            let answer = try XCTUnwrap(askVM.answer)
            XCTAssertFalse(answer.answer.isEmpty, "AI answer should be non-empty")
            // Citations may be 0 if the prompt didn't trigger a Sources block; require >=1
            // when the demo seed is present (we already asserted that above).
            XCTAssertGreaterThanOrEqual(
                answer.citations.count,
                1,
                "Demo KB + answer prompt should produce at least one citation"
            )
        } else {
            XCTAssertTrue(askVM.aiDisabled, "ai_enabled=false should flip AskKBViewModel.aiDisabled")
            XCTAssertEqual(askVM.errorMessage, APIError.aiDisabled.userMessage)
        }
    }

    // MARK: - Helpers

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
