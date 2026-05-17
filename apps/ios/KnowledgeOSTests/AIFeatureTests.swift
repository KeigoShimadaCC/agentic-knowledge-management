import XCTest
@testable import KnowledgeOS

@MainActor
final class AIFeatureTests: XCTestCase {
    // MARK: - DTO decoding

    func testSummarizeResponseDecodes() throws {
        let response = try FixtureLoader.decode(SummarizeResponseDTO.self, named: "ai_summarize")
        XCTAssertEqual(response.summary, "KnowledgeOS lets you dump, structure, search, and reason over personal knowledge.")
        XCTAssertFalse(response.cached)
    }

    func testSuggestLinksResponseDecodes() throws {
        let response = try FixtureLoader.decode(SuggestLinksResponseDTO.self, named: "ai_suggest_links")
        XCTAssertEqual(response.suggestions.count, 2)
        XCTAssertEqual(response.suggestions.first?.confidence ?? 0.0, 0.83, accuracy: 0.001)
        XCTAssertEqual(response.suggestions.last?.targetKind, "source")
    }

    func testAIDisabledErrorMapsFromFixture() throws {
        let data = try FixtureLoader.data(named:"error_ai_disabled")
        let error = APIError.from(httpStatus: 503, data: data)
        XCTAssertEqual(error, .aiDisabled)
    }

    func testAIDisabledErrorMapsOnlyOn503() throws {
        // Spec: ai_disabled is signaled by 503 + code=ai_disabled. Non-503 stays a validation error.
        let data = try FixtureLoader.data(named: "error_ai_disabled")
        XCTAssertEqual(APIError.from(httpStatus: 400, data: data), .validation("AI features are disabled."))
    }

    // MARK: - AskKBViewModel

    func testAskKBViewModelHandlesAIDisabled() async {
        let stub = StubAIClient(behavior: .failWith(APIError.aiDisabled))
        let api = AIAPI(apiClient: stub, keychain: InMemoryKeychain())
        let vm = AskKBViewModel(api: api)
        vm.query = "what is knowledgeos"

        await vm.ask()

        XCTAssertTrue(vm.aiDisabled)
        XCTAssertEqual(vm.errorMessage, APIError.aiDisabled.userMessage)
        XCTAssertNil(vm.answer)
    }

    func testAskKBViewModelDeliversAnswer() async throws {
        let data = try FixtureLoader.data(named:"answer")
        let stub = StubAIClient(behavior: .succeedWith(data))
        let api = AIAPI(apiClient: stub, keychain: InMemoryKeychain())
        let vm = AskKBViewModel(api: api)
        vm.query = "what is knowledgeos"

        await vm.ask()

        XCTAssertNotNil(vm.answer)
        XCTAssertEqual(vm.answer?.citations.count, 1)
        XCTAssertNil(vm.errorMessage)
    }

    func testAskKBViewModelTrimsAndGuardsBlankQueries() async {
        let stub = StubAIClient(behavior: .recordOnly)
        let api = AIAPI(apiClient: stub, keychain: InMemoryKeychain())
        let vm = AskKBViewModel(api: api)
        vm.query = "   "

        await vm.ask()

        XCTAssertFalse(stub.didRequest)
    }

    func testCanSubmitRespectsAIDisabled() {
        let stub = StubAIClient(behavior: .recordOnly)
        let api = AIAPI(apiClient: stub, keychain: InMemoryKeychain())
        let vm = AskKBViewModel(api: api)
        vm.query = "hello"
        XCTAssertTrue(vm.canSubmit)
        vm.setAIDisabled(true)
        XCTAssertFalse(vm.canSubmit)
    }
}

// MARK: - Test doubles

private final class StubAIClient: APIClientProtocol, @unchecked Sendable {
    enum Behavior {
        case succeedWith(Data)
        case failWith(APIError)
        case recordOnly
    }

    private let behavior: Behavior
    private(set) var didRequest: Bool = false
    var bearerToken: String? = "test-token"

    init(behavior: Behavior) { self.behavior = behavior }

    func request<T: Decodable>(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> T {
        didRequest = true
        switch behavior {
        case let .succeedWith(data):
            return try JSONCoding.decoder.decode(T.self, from: data)
        case let .failWith(error):
            throw error
        case .recordOnly:
            throw APIError.serverError
        }
    }

    func requestData(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> Data {
        didRequest = true
        switch behavior {
        case let .succeedWith(data): return data
        case let .failWith(error): throw error
        case .recordOnly: throw APIError.serverError
        }
    }

    func uploadMultipart(_ endpoint: APIEndpoint, upload: MultipartUpload, auth: Bool) async throws -> Data {
        throw APIError.serverError
    }

    func setBearerToken(_ token: String?) { bearerToken = token }
    func setUnauthorizedHandler(_ handler: (@Sendable () async -> Void)?) {}
}

private struct InMemoryKeychain: KeychainStore {
    func saveToken(_ token: String) throws {}
    func readToken() throws -> String? { "test-token" }
    func deleteToken() throws {}
}
