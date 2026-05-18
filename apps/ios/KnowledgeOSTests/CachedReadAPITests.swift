import XCTest
@testable import KnowledgeOS

@MainActor
final class CachedReadAPITests: XCTestCase {
    func testColdCacheYieldsFreshOnly() async throws {
        let cache = InMemoryCacheStore()
        let fixture = try FixtureLoader.data(named: "object")
        let stub = StubAPIClient(behavior: .succeedWith(fixture))
        let api = CachedReadAPI(read: ReadAPI(apiClient: stub, keychain: InMemoryKeychainStub()), cache: cache)

        var values: [ObjectDTO] = []
        for await result in api.object(id: UUID(uuidString: "22222222-2222-2222-2222-222222222222")!) {
            if case let .success(v) = result { values.append(v) }
        }
        XCTAssertEqual(values.count, 1)
        XCTAssertEqual(values.first?.title, "Sample Page")
    }

    func testWarmCacheYieldsCachedThenFresh() async throws {
        let cache = InMemoryCacheStore()
        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        try cache.saveObject(object)

        let fixture = try FixtureLoader.data(named: "object")
        let stub = StubAPIClient(behavior: .succeedWith(fixture))
        let api = CachedReadAPI(read: ReadAPI(apiClient: stub, keychain: InMemoryKeychainStub()), cache: cache)

        var values: [ObjectDTO] = []
        for await result in api.object(id: object.id) {
            if case let .success(v) = result { values.append(v) }
        }
        // Cached + fresh = 2 yields.
        XCTAssertEqual(values.count, 2)
    }

    func testFailureWithWarmCacheSwallowsError() async throws {
        let cache = InMemoryCacheStore()
        let object = try FixtureLoader.decode(ObjectDTO.self, named: "object")
        try cache.saveObject(object)

        let stub = StubAPIClient(behavior: .failWith(.serverError))
        let api = CachedReadAPI(read: ReadAPI(apiClient: stub, keychain: InMemoryKeychainStub()), cache: cache)

        var successes: Int = 0
        var failures: Int = 0
        for await result in api.object(id: object.id) {
            switch result {
            case .success: successes += 1
            case .failure: failures += 1
            }
        }
        XCTAssertEqual(successes, 1)
        XCTAssertEqual(failures, 0)
    }

    func testFailureWithColdCacheYieldsError() async throws {
        let cache = InMemoryCacheStore()
        let stub = StubAPIClient(behavior: .failWith(.serverError))
        let api = CachedReadAPI(read: ReadAPI(apiClient: stub, keychain: InMemoryKeychainStub()), cache: cache)

        var successes: Int = 0
        var failures: [APIError] = []
        for await result in api.object(id: UUID()) {
            switch result {
            case .success: successes += 1
            case let .failure(err): failures.append(err)
            }
        }
        XCTAssertEqual(successes, 0)
        XCTAssertEqual(failures, [.serverError])
    }

    func testRecentObjectsSavesToCache() async throws {
        let cache = InMemoryCacheStore()
        let fixture = try FixtureLoader.data(named: "paginated_objects")
        let stub = StubAPIClient(behavior: .succeedWith(fixture))
        let api = CachedReadAPI(read: ReadAPI(apiClient: stub, keychain: InMemoryKeychainStub()), cache: cache)

        for await _ in api.recentObjects(page: 1) {}

        XCTAssertNotNil(cache.cachedRecentObjects(page: 1))
    }
}

// MARK: - Test doubles shared across PHONE-05 tests

final class StubAPIClient: APIClientProtocol, @unchecked Sendable {
    enum Behavior {
        case succeedWith(Data)
        case failWith(APIError)
    }

    private let behavior: Behavior
    var bearerToken: String? = "test-token"
    private(set) var lastDataEndpoint: APIEndpoint?
    private(set) var lastDataAuth: Bool?

    init(behavior: Behavior) { self.behavior = behavior }

    func request<T: Decodable>(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> T {
        switch behavior {
        case let .succeedWith(data):
            return try JSONCoding.decoder.decode(T.self, from: data)
        case let .failWith(error):
            throw error
        }
    }

    func requestData(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> Data {
        lastDataEndpoint = endpoint
        lastDataAuth = auth
        switch behavior {
        case let .succeedWith(data): return data
        case let .failWith(error): throw error
        }
    }

    func uploadMultipart(_ endpoint: APIEndpoint, upload: MultipartUpload, auth: Bool) async throws -> Data {
        switch behavior {
        case let .succeedWith(data): return data
        case let .failWith(error): throw error
        }
    }

    func setBearerToken(_ token: String?) { bearerToken = token }
    func setUnauthorizedHandler(_ handler: (@Sendable () async -> Void)?) {}
}

struct InMemoryKeychainStub: KeychainStore {
    func readToken() throws -> String? { "test-token" }
    func saveToken(_ token: String) throws {}
    func deleteToken() throws {}
}
