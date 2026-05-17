import XCTest
@testable import KnowledgeOS

@MainActor
final class AuthStoreTests: XCTestCase {
    func testLoginPersistsTokenAndBootstraps() async throws {
        let keychain = InMemoryKeychainStore()
        let mock = MockAPIClient()
        mock.loginResponse = try FixtureLoader.decode(MobileLoginResponse.self, named: "mobile_login_response")
        mock.bootstrapResponse = try FixtureLoader.decode(MobileBootstrapResponse.self, named: "mobile_bootstrap_response")

        let store = AuthStore(apiClient: mock, keychain: keychain)
        await store.login(email: "mobile@test.com", password: "password123", deviceName: "Test iPhone")

        XCTAssertTrue(store.isAuthenticated)
        XCTAssertEqual(store.currentUser?.displayName, "Mobile User")
        XCTAssertEqual(try keychain.readToken(), "test-mobile-token-opaque")
        XCTAssertEqual(mock.bearerToken, "test-mobile-token-opaque")
    }

    func testLogoutClearsKeychain() async throws {
        let keychain = InMemoryKeychainStore()
        try keychain.saveToken("token-to-clear")
        let mock = MockAPIClient()
        mock.bootstrapResponse = try FixtureLoader.decode(MobileBootstrapResponse.self, named: "mobile_bootstrap_response")

        let store = AuthStore(apiClient: mock, keychain: keychain)
        mock.setBearerToken("token-to-clear")
        await store.restoreSessionIfNeeded()
        XCTAssertTrue(store.isAuthenticated)

        await store.logout()
        XCTAssertFalse(store.isAuthenticated)
        XCTAssertNil(try keychain.readToken())
        XCTAssertNil(mock.bearerToken)
    }

    func testBaseURLChangeClearsSession() async throws {
        let keychain = InMemoryKeychainStore()
        try keychain.saveToken("token-to-clear")
        let mock = MockAPIClient()
        mock.bootstrapResponse = try FixtureLoader.decode(MobileBootstrapResponse.self, named: "mobile_bootstrap_response")

        let store = AuthStore(apiClient: mock, keychain: keychain)
        mock.setBearerToken("token-to-clear")
        await store.restoreSessionIfNeeded()
        XCTAssertTrue(store.isAuthenticated)

        store.onBaseURLChanged(from: "http://127.0.0.1:8001", to: "http://192.168.1.10:8001")
        try await Task.sleep(nanoseconds: 100_000_000)

        XCTAssertFalse(store.isAuthenticated)
        XCTAssertNil(try keychain.readToken())
    }

    func testRestoreSessionWithoutTokenDoesNotAuthenticate() async {
        let store = AuthStore(apiClient: MockAPIClient(), keychain: InMemoryKeychainStore())
        await store.restoreSessionIfNeeded()
        XCTAssertFalse(store.isAuthenticated)
    }
}

@MainActor
final class MockAPIClient: APIClientProtocol, @unchecked Sendable {
    var bearerToken: String?
    var loginResponse: MobileLoginResponse?
    var bootstrapResponse: MobileBootstrapResponse?
    var logoutCalled = false
    private var unauthorizedHandler: (@Sendable () async -> Void)?

    func setBearerToken(_ token: String?) {
        bearerToken = token
    }

    func setUnauthorizedHandler(_ handler: (@Sendable () async -> Void)?) {
        unauthorizedHandler = handler
    }

    func request<T: Decodable>(
        _ endpoint: APIEndpoint,
        body: (any Encodable)?,
        auth: Bool
    ) async throws -> T {
        switch endpoint.path {
        case "/api/v1/auth/mobile-login":
            guard let loginResponse else {
                throw APIError.serverError
            }
            return loginResponse as! T
        case "/api/v1/mobile/bootstrap":
            guard let bootstrapResponse else {
                throw APIError.serverError
            }
            return bootstrapResponse as! T
        case "/api/v1/auth/mobile-logout":
            logoutCalled = true
            return OkResponse(ok: true) as! T
        default:
            throw APIError.notFound
        }
    }

    func requestData(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> Data {
        throw APIError.serverError
    }

    func uploadMultipart(_ endpoint: APIEndpoint, upload: MultipartUpload, auth: Bool) async throws -> Data {
        throw APIError.serverError
    }
}
