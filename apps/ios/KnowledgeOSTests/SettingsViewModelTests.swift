import XCTest
@testable import KnowledgeOS

@MainActor
final class SettingsViewModelTests: XCTestCase {
  func testLoadSetsSettingsAndClearsError() async throws {
    let settingsData = try FixtureLoader.data(named: "settings")
    let stub = SettingsRoutingStubAPIClient(
      routes: [
        "/api/v1/settings": .data(settingsData),
        "/api/v1/mcp-connections/": .data(Data("[]".utf8)),
      ]
    )
    let vm = SettingsViewModel(api: SettingsAPI(apiClient: stub, keychain: InMemoryKeychainStub()))

    await vm.load()

    XCTAssertNotNil(vm.settings)
    XCTAssertNil(vm.errorMessage)
    XCTAssertFalse(vm.isLoading)
    XCTAssertEqual(vm.settings?.features.first?.featureKey, "summarize")
  }

  func testLoadOnFailureSetsErrorMessage() async {
    let stub = SettingsRoutingStubAPIClient(
      routes: ["/api/v1/settings": .failWith(.serverError)]
    )
    let vm = SettingsViewModel(api: SettingsAPI(apiClient: stub, keychain: InMemoryKeychainStub()))

    await vm.load()

    XCTAssertNil(vm.settings)
    XCTAssertNotNil(vm.errorMessage)
    XCTAssertFalse(vm.isLoading)
  }

  func testSaveFeatureUpdatesResolvedModel() async throws {
    let settingsData = try FixtureLoader.data(named: "settings")
    let updatedFeature = """
    {
      "feature_key": "summarize",
      "display_name": "Summarization",
      "enabled": true,
      "provider": "openai",
      "model": "gpt-custom",
      "temperature": 0.2,
      "max_tokens": 2000,
      "effort": null,
      "resolved_provider": "openai",
      "resolved_model": "gpt-custom",
      "resolved_temperature": 0.2,
      "resolved_max_tokens": 2000,
      "supports_effort": false,
      "note": null
    }
    """
    let stub = SettingsRoutingStubAPIClient(
      routes: [
        "/api/v1/settings": .data(settingsData),
        "/api/v1/mcp-connections/": .data(Data("[]".utf8)),
        "/api/v1/settings/ai-features/summarize": .data(Data(updatedFeature.utf8)),
      ]
    )
    let vm = SettingsViewModel(api: SettingsAPI(apiClient: stub, keychain: InMemoryKeychainStub()))
    await vm.load()
    guard let feature = vm.settings?.features.first(where: { $0.featureKey == "summarize" }) else {
      return XCTFail("missing summarize feature")
    }

    await vm.saveFeature(
      feature,
      enabled: true,
      provider: "openai",
      model: "gpt-custom",
      temperature: 0.2,
      maxTokens: 2000
    )

    XCTAssertEqual(vm.settings?.features.first(where: { $0.featureKey == "summarize" })?.resolvedModel, "gpt-custom")
    XCTAssertEqual(vm.statusMessage, "Saved")
  }

  func testSavePromptUpdatesPromptInSettings() async throws {
    let settingsData = try FixtureLoader.data(named: "settings")
    let updatedPrompt = """
    {
      "key": "summarize.page",
      "display_name": "Summarize Page",
      "default_template": "Summarize {content}",
      "effective_template": "Override {content}",
      "override_template": "Override {content}",
      "has_override": true,
      "variables": ["content"],
      "response_contract": "Plain text summary.",
      "updated_at": null
    }
    """
    let stub = SettingsRoutingStubAPIClient(
      routes: [
        "/api/v1/settings": .data(settingsData),
        "/api/v1/mcp-connections/": .data(Data("[]".utf8)),
        "/api/v1/settings/prompts/summarize.page": .data(Data(updatedPrompt.utf8)),
      ]
    )
    let vm = SettingsViewModel(api: SettingsAPI(apiClient: stub, keychain: InMemoryKeychainStub()))
    await vm.load()
    guard let prompt = vm.settings?.prompts.first(where: { $0.key == "summarize.page" }) else {
      return XCTFail("missing summarize.page prompt")
    }

    await vm.savePrompt(prompt, template: "Override {content}")

    let saved = vm.settings?.prompts.first(where: { $0.key == "summarize.page" })
    XCTAssertEqual(saved?.hasOverride, true)
    XCTAssertEqual(saved?.effectiveTemplate, "Override {content}")
  }

  func testResetPromptClearsOverride() async throws {
    var settingsData = try FixtureLoader.data(named: "settings")
    if var root = try JSONSerialization.jsonObject(with: settingsData) as? [String: Any],
      var prompts = root["prompts"] as? [[String: Any]],
      !prompts.isEmpty
    {
      prompts[0]["has_override"] = true
      prompts[0]["override_template"] = "Custom {content}"
      root["prompts"] = prompts
      settingsData = try JSONSerialization.data(withJSONObject: root)
    }

    let resetPrompt = """
    {
      "key": "summarize.page",
      "display_name": "Summarize Page",
      "default_template": "Summarize {content}",
      "effective_template": "Summarize {content}",
      "override_template": null,
      "has_override": false,
      "variables": ["content"],
      "response_contract": "Plain text summary.",
      "updated_at": null
    }
    """
    let stub = SettingsRoutingStubAPIClient(
      routes: [
        "/api/v1/settings": .data(settingsData),
        "/api/v1/mcp-connections/": .data(Data("[]".utf8)),
        "/api/v1/settings/prompts/summarize.page/reset": .data(Data(resetPrompt.utf8)),
      ]
    )
    let vm = SettingsViewModel(api: SettingsAPI(apiClient: stub, keychain: InMemoryKeychainStub()))
    await vm.load()
    guard let prompt = vm.settings?.prompts.first(where: { $0.key == "summarize.page" }) else {
      return XCTFail("missing summarize.page prompt")
    }

    await vm.resetPrompt(prompt)

    let saved = vm.settings?.prompts.first(where: { $0.key == "summarize.page" })
    XCTAssertEqual(saved?.hasOverride, false)
    XCTAssertEqual(vm.statusMessage, "Reset")
  }

  func testSaveSecretsSetsStatusMessage() async throws {
    let settingsData = try FixtureLoader.data(named: "settings")
    let stub = SettingsRoutingStubAPIClient(
      routes: [
        "/api/v1/settings": .data(settingsData),
        "/api/v1/mcp-connections/": .data(Data("[]".utf8)),
        "/api/v1/settings/secrets": .data(settingsData),
      ]
    )
    let vm = SettingsViewModel(api: SettingsAPI(apiClient: stub, keychain: InMemoryKeychainStub()))
    await vm.load()

    await vm.saveSecrets(openAIKey: "sk-test", anthropicKey: "")

    XCTAssertNotNil(vm.settings)
    XCTAssertEqual(vm.statusMessage, "Saved")
  }
}

// MARK: - Routing stub

final class SettingsRoutingStubAPIClient: APIClientProtocol, @unchecked Sendable {
  enum RouteValue {
    case data(Data)
    case failWith(APIError)
  }

  private let routes: [String: RouteValue]

  init(routes: [String: RouteValue]) {
    self.routes = routes
  }

  var bearerToken: String? = "test-token"

  func request<T: Decodable>(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> T {
    let path = endpoint.path
    switch routes[path] {
    case let .data(data):
      return try JSONCoding.decoder.decode(T.self, from: data)
    case let .failWith(error):
      throw error
    case .none:
      throw APIError.serverError
    }
  }

  func requestData(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> Data {
    switch routes[endpoint.path] {
    case let .data(data):
      return data
    case let .failWith(error):
      throw error
    case .none:
      throw APIError.serverError
    }
  }

  func uploadMultipart(_ endpoint: APIEndpoint, upload: MultipartUpload, auth: Bool) async throws -> Data {
    throw APIError.serverError
  }

  func setBearerToken(_ token: String?) { bearerToken = token }
  func setUnauthorizedHandler(_ handler: (@Sendable () async -> Void)?) {}
}
