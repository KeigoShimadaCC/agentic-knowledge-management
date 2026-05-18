import Foundation

struct SecretStatusDTO: Codable, Equatable {
    let key: String
    let configured: Bool
    let source: String
    let redacted: String?
    let lastTestStatus: String?
    let lastTestError: String?
    let lastTestedAt: Date?
}

struct AIFeatureSettingDTO: Codable, Equatable, Identifiable {
    var id: String { featureKey }
    let featureKey: String
    let displayName: String
    let enabled: Bool
    let provider: String?
    let model: String?
    let temperature: Double?
    let maxTokens: Int?
    let effort: String?
    let resolvedProvider: String?
    let resolvedModel: String?
    let resolvedTemperature: Double?
    let resolvedMaxTokens: Int?
    let supportsEffort: Bool
    let note: String?
}

struct PromptDTO: Codable, Equatable, Identifiable {
    var id: String { key }
    let key: String
    let displayName: String
    let defaultTemplate: String
    let effectiveTemplate: String
    let overrideTemplate: String?
    let hasOverride: Bool
    let variables: [String]
    let responseContract: String
    let updatedAt: Date?
}

struct EnvExportStatusDTO: Codable, Equatable {
    let available: Bool
    let path: String?
    let lastWarning: String?
    let allowlistedKeys: [String]
}

struct BackgroundAISettingsDTO: Codable, Equatable {
    let enabled: Bool
    let tasks: [String]
}

struct MCPSettingsSummaryDTO: Codable, Equatable {
    let connectionCount: Int
    let enabledCount: Int
    let webSearchThreshold: Double
    let webSearchConnectionName: String?
}

struct MCPConnectionDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let name: String
    let transport: String
    let url: String?
    let enabled: Bool
    let lastTestedAt: Date?
    let lastError: String?
}

struct MCPConnectionPatchDTO: Encodable {
    let enabled: Bool?
}

struct MCPConnectionTestResultDTO: Decodable {
    let ok: Bool
    let error: String?
}

struct SettingsResponseDTO: Codable, Equatable {
    let secrets: [SecretStatusDTO]
    let features: [AIFeatureSettingDTO]
    let prompts: [PromptDTO]
    let backgroundAi: BackgroundAISettingsDTO
    let mcp: MCPSettingsSummaryDTO
    let envExport: EnvExportStatusDTO
}

struct SettingsSecretPatch: Encodable {
    let openaiApiKey: String?
    let anthropicApiKey: String?
    let clearOpenaiApiKey: Bool
    let clearAnthropicApiKey: Bool
    let exportEnv: Bool
}

struct AIFeatureSettingPatchDTO: Encodable {
    let enabled: Bool?
    let provider: String?
    let model: String?
    let temperature: Double?
    let maxTokens: Int?
    let effort: String?
}

struct PromptPatchDTO: Encodable {
    let template: String
}

struct BackgroundAIPatchDTO: Encodable {
    let enabled: Bool
    let tasks: [String]
}
