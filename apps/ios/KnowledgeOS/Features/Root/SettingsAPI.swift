import Foundation
import Observation

struct SettingsAPI: Sendable {
    private let apiClient: any APIClientProtocol
    private let keychain: any KeychainStore

    init(
        apiClient: any APIClientProtocol = APIClient(),
        keychain: any KeychainStore = SystemKeychainStore()
    ) {
        self.apiClient = apiClient
        self.keychain = keychain
    }

    private func prepare() throws {
        if apiClient.bearerToken == nil {
            apiClient.setBearerToken(try keychain.readToken())
        }
    }

    func load() async throws -> SettingsResponseDTO {
        try prepare()
        return try await apiClient.request(.settings, body: nil as String?, auth: true)
    }

    func saveSecrets(openAIKey: String?, anthropicKey: String?) async throws -> SettingsResponseDTO {
        try prepare()
        let body = SettingsSecretPatch(
            openaiApiKey: openAIKey,
            anthropicApiKey: anthropicKey,
            clearOpenaiApiKey: false,
            clearAnthropicApiKey: false,
            exportEnv: true
        )
        return try await apiClient.request(.settingsSecrets, body: body, auth: true)
    }

    func saveFeature(_ featureKey: String, patch: AIFeatureSettingPatchDTO) async throws -> AIFeatureSettingDTO {
        try prepare()
        return try await apiClient.request(.settingsFeature(featureKey), body: patch, auth: true)
    }

    func saveBackgroundAI(enabled: Bool, tasks: [String]) async throws -> BackgroundAISettingsDTO {
        try prepare()
        return try await apiClient.request(
            .settingsBackgroundAI,
            body: BackgroundAIPatchDTO(enabled: enabled, tasks: tasks),
            auth: true
        )
    }

    func listMCPConnections() async throws -> [MCPConnectionDTO] {
        try prepare()
        return try await apiClient.request(.mcpConnections, body: nil as String?, auth: true)
    }

    func setMCPConnectionEnabled(_ id: UUID, enabled: Bool) async throws -> MCPConnectionDTO {
        try prepare()
        return try await apiClient.request(
            .mcpConnection(id),
            body: MCPConnectionPatchDTO(enabled: enabled),
            auth: true
        )
    }

    func testMCPConnection(_ id: UUID) async throws -> MCPConnectionTestResultDTO {
        try prepare()
        return try await apiClient.request(.mcpConnectionTest(id), body: nil as String?, auth: true)
    }

    func savePrompt(_ promptKey: String, template: String) async throws -> PromptDTO {
        try prepare()
        return try await apiClient.request(
            .settingsPrompt(promptKey),
            body: PromptPatchDTO(template: template),
            auth: true
        )
    }

    func resetPrompt(_ promptKey: String) async throws -> PromptDTO {
        try prepare()
        return try await apiClient.request(.settingsPromptReset(promptKey), body: nil as String?, auth: true)
    }
}

@MainActor
@Observable
final class SettingsViewModel {
    var settings: SettingsResponseDTO?
    var isLoading = false
    var errorMessage: String?
    var statusMessage: String?
    var mcpConnections: [MCPConnectionDTO] = []

    private let api: SettingsAPI

    init(api: SettingsAPI = SettingsAPI()) {
        self.api = api
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            settings = try await api.load()
        } catch {
            errorMessage = error.localizedDescription
        }
        do {
            mcpConnections = try await api.listMCPConnections()
        } catch {
            if errorMessage == nil {
                errorMessage = error.localizedDescription
            }
        }
        isLoading = false
    }

    func saveSecrets(openAIKey: String, anthropicKey: String) async {
        do {
            settings = try await api.saveSecrets(
                openAIKey: openAIKey.isEmpty ? nil : openAIKey,
                anthropicKey: anthropicKey.isEmpty ? nil : anthropicKey
            )
            statusMessage = settings?.envExport.lastWarning ?? "Saved"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func saveFeature(_ feature: AIFeatureSettingDTO) async {
        do {
            let saved = try await api.saveFeature(
                feature.featureKey,
                patch: AIFeatureSettingPatchDTO(
                    enabled: feature.enabled,
                    provider: feature.resolvedProvider,
                    model: feature.resolvedModel,
                    temperature: feature.resolvedTemperature,
                    maxTokens: feature.resolvedMaxTokens,
                    effort: feature.effort
                )
            )
            replaceFeature(saved)
            statusMessage = "Saved"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func saveFeature(
        _ feature: AIFeatureSettingDTO,
        enabled: Bool,
        provider: String?,
        model: String?,
        temperature: Double?,
        maxTokens: Int?
    ) async {
        do {
            let saved = try await api.saveFeature(
                feature.featureKey,
                patch: AIFeatureSettingPatchDTO(
                    enabled: enabled,
                    provider: provider,
                    model: model,
                    temperature: temperature,
                    maxTokens: maxTokens,
                    effort: feature.effort
                )
            )
            replaceFeature(saved)
            statusMessage = "Saved"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func saveBackgroundAI(enabled: Bool, tasks: [String]) async {
        do {
            let saved = try await api.saveBackgroundAI(enabled: enabled, tasks: tasks)
            guard let current = settings else { return }
            settings = SettingsResponseDTO(
                secrets: current.secrets,
                features: current.features,
                prompts: current.prompts,
                backgroundAi: saved,
                mcp: current.mcp,
                envExport: current.envExport
            )
            statusMessage = "Saved"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func setMCPConnectionEnabled(_ connection: MCPConnectionDTO, enabled: Bool) async {
        do {
            let saved = try await api.setMCPConnectionEnabled(connection.id, enabled: enabled)
            mcpConnections = mcpConnections.map { $0.id == saved.id ? saved : $0 }
            statusMessage = "Saved"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func testMCPConnection(_ connection: MCPConnectionDTO) async {
        do {
            let result = try await api.testMCPConnection(connection.id)
            statusMessage = result.ok ? "MCP test succeeded" : (result.error ?? "MCP test failed")
            mcpConnections = try await api.listMCPConnections()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func savePrompt(_ prompt: PromptDTO, template: String) async {
        do {
            let saved = try await api.savePrompt(prompt.key, template: template)
            replacePrompt(saved)
            statusMessage = "Saved"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func resetPrompt(_ prompt: PromptDTO) async {
        do {
            let saved = try await api.resetPrompt(prompt.key)
            replacePrompt(saved)
            statusMessage = "Reset"
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func replaceFeature(_ feature: AIFeatureSettingDTO) {
        guard var current = settings else { return }
        current = SettingsResponseDTO(
            secrets: current.secrets,
            features: current.features.map { $0.featureKey == feature.featureKey ? feature : $0 },
            prompts: current.prompts,
            backgroundAi: current.backgroundAi,
            mcp: current.mcp,
            envExport: current.envExport
        )
        settings = current
    }

    private func replacePrompt(_ prompt: PromptDTO) {
        guard var current = settings else { return }
        current = SettingsResponseDTO(
            secrets: current.secrets,
            features: current.features,
            prompts: current.prompts.map { $0.key == prompt.key ? prompt : $0 },
            backgroundAi: current.backgroundAi,
            mcp: current.mcp,
            envExport: current.envExport
        )
        settings = current
    }
}
