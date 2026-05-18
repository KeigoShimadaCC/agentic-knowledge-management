import SwiftUI

struct SettingsTab: View {
    @Environment(AuthStore.self) private var authStore
    @EnvironmentObject private var appState: AppState
    @State private var viewModel = SettingsViewModel()
    @State private var openAIKey = ""
    @State private var anthropicKey = ""
    @State private var showingLANWarning = false
    let onLogout: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                if let user = authStore.currentUser {
                    Section("Account") {
                        LabeledContent("Email", value: user.email)
                        LabeledContent("Name", value: user.displayName)
                    }
                }

                if let capabilities = authStore.capabilities {
                    Section("Server") {
                        LabeledContent("Base URL", value: appState.baseURLString)
                    }

                    Section("About") {
                        LabeledContent("Mobile API", value: "\(capabilities.mobileApiVersion)")
                        LabeledContent("AI", value: capabilities.aiEnabled ? "On" : "Off")
                        LabeledContent("Embeddings", value: capabilities.embeddingsEnabled ? "On" : "Off")
                        LabeledContent("Upload", value: capabilities.uploadEnabled ? "On" : "Off")
                    }
                }

                if viewModel.isLoading {
                    Section {
                        ProgressView()
                    }
                }

                if let error = viewModel.errorMessage {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                            .accessibilityIdentifier("kos.settings.error")
                    }
                }

                if let settings = viewModel.settings {
                    Section("AI Providers") {
                        ForEach(settings.secrets, id: \.key) { secret in
                            VStack(alignment: .leading, spacing: 4) {
                                LabeledContent(providerName(secret.key), value: secret.configured ? secret.source : "Off")
                                if let redacted = secret.redacted {
                                    Text(redacted)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                if let lastError = secret.lastTestError {
                                    Text(lastError)
                                        .font(.caption)
                                        .foregroundStyle(.red)
                                }
                            }
                        }
                    }

                    Section("Secret Entry") {
                        SecureField("OpenAI API key", text: $openAIKey)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .accessibilityIdentifier("kos.settings.openaiKey")
                        SecureField("Anthropic API key", text: $anthropicKey)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .accessibilityIdentifier("kos.settings.anthropicKey")
                        Button("Save Keys") {
                            showingLANWarning = true
                        }
                        .accessibilityIdentifier("kos.settings.saveKeys")
                    }

                    Section("Feature Models") {
                        ForEach(settings.features) { feature in
                            NavigationLink {
                                FeatureSettingsEditor(feature: feature, viewModel: viewModel)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(feature.displayName)
                                    Text("\(feature.resolvedProvider ?? "none") / \(feature.resolvedModel ?? "none")")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .accessibilityIdentifier("kos.settings.feature.\(feature.featureKey)")
                        }
                    }

                    Section("Background AI") {
                        BackgroundAIEditor(settings: settings.backgroundAi, viewModel: viewModel)
                    }

                    Section("Prompts") {
                        ForEach(settings.prompts) { prompt in
                            NavigationLink {
                                PromptOverrideEditor(prompt: prompt, viewModel: viewModel)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(prompt.displayName)
                                    Text(prompt.hasOverride ? "Override" : prompt.responseContract)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .accessibilityIdentifier("kos.settings.prompt.\(prompt.key)")
                        }
                    }

                    Section("MCP") {
                        LabeledContent("Connections", value: "\(settings.mcp.enabledCount)/\(settings.mcp.connectionCount)")
                        LabeledContent("Web threshold", value: "\(settings.mcp.webSearchThreshold)")
                        if let name = settings.mcp.webSearchConnectionName {
                            LabeledContent("Preferred", value: name)
                        }
                        Text("Stdio connections are read-only on phone.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        ForEach(viewModel.mcpConnections) { connection in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    VStack(alignment: .leading) {
                                        Text(connection.name)
                                        Text(connection.transport)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Toggle("Enabled", isOn: Binding(
                                        get: { connection.enabled },
                                        set: { value in
                                            Task { await viewModel.setMCPConnectionEnabled(connection, enabled: value) }
                                        }
                                    ))
                                    .labelsHidden()
                                    .disabled(connection.transport == "stdio")
                                }
                                if connection.transport != "stdio" {
                                    Button("Test") {
                                        Task { await viewModel.testMCPConnection(connection) }
                                    }
                                    .font(.caption)
                                    .accessibilityIdentifier("kos.settings.mcp.test.\(connection.id.uuidString)")
                                }
                                if let error = connection.lastError {
                                    Text(error)
                                        .font(.caption)
                                        .foregroundStyle(.red)
                                }
                            }
                        }
                    }

                    Section("Diagnostics") {
                        LabeledContent("Env export", value: settings.envExport.available ? "Available" : "Unavailable")
                        if let path = settings.envExport.path {
                            Text(path)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        if let warning = settings.envExport.lastWarning {
                            Text(warning)
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
                    }
                }

                if let status = viewModel.statusMessage {
                    Section {
                        Text(status)
                            .foregroundStyle(.secondary)
                            .accessibilityIdentifier("kos.settings.status")
                    }
                }
            }
            .navigationTitle("Settings")
            .accessibilityIdentifier("kos.settings.screen")
            .task {
                await viewModel.load()
            }
            .refreshable {
                await viewModel.load()
            }
            .alert("LAN Secret Warning", isPresented: $showingLANWarning) {
                Button("Cancel", role: .cancel) {}
                Button("Save") {
                    Task {
                        await viewModel.saveSecrets(openAIKey: openAIKey, anthropicKey: anthropicKey)
                        openAIKey = ""
                        anthropicKey = ""
                    }
                }
            } message: {
                Text("Only submit keys to a trusted HTTPS or local LAN KnowledgeOS server. Keys are sent to the backend and are not stored in iOS Keychain.")
            }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Sign Out", role: .destructive) {
                        onLogout()
                    }
                    .accessibilityIdentifier("kos.settings.logoutButton")
                }
            }
        }
    }

    private func providerName(_ key: String) -> String {
        key == "openai_api_key" ? "OpenAI" : "Anthropic"
    }
}

private struct FeatureSettingsEditor: View {
    let feature: AIFeatureSettingDTO
    let viewModel: SettingsViewModel
    @State private var enabled: Bool
    @State private var provider: String
    @State private var model: String
    @State private var temperature: String
    @State private var maxTokens: String

    init(feature: AIFeatureSettingDTO, viewModel: SettingsViewModel) {
        self.feature = feature
        self.viewModel = viewModel
        _enabled = State(initialValue: feature.enabled)
        _provider = State(initialValue: feature.provider ?? feature.resolvedProvider ?? "openai")
        _model = State(initialValue: feature.model ?? feature.resolvedModel ?? "")
        _temperature = State(initialValue: String(feature.temperature ?? feature.resolvedTemperature ?? 0.2))
        _maxTokens = State(initialValue: String(feature.maxTokens ?? feature.resolvedMaxTokens ?? 2000))
    }

    var body: some View {
        Form {
            Toggle("Enabled", isOn: $enabled)
            Picker("Provider", selection: $provider) {
                Text("OpenAI").tag("openai")
                Text("Anthropic").tag("anthropic")
            }
            TextField("Model", text: $model)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            TextField("Temperature", text: $temperature)
                .keyboardType(.decimalPad)
            TextField("Max tokens", text: $maxTokens)
                .keyboardType(.numberPad)
            Button("Save") {
                Task {
                    await viewModel.saveFeature(
                        feature,
                        enabled: enabled,
                        provider: provider,
                        model: model.isEmpty ? nil : model,
                        temperature: Double(temperature),
                        maxTokens: Int(maxTokens)
                    )
                }
            }
            .accessibilityIdentifier("kos.settings.featureSave")
        }
        .navigationTitle(feature.displayName)
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct BackgroundAIEditor: View {
    let settings: BackgroundAISettingsDTO
    let viewModel: SettingsViewModel
    @State private var enabled: Bool
    @State private var tasks: Set<String>

    private let options = [
        ("summarize", "Summarize"),
        ("extract_claims", "Extract claims"),
        ("suggest_links", "Suggest links"),
    ]

    init(settings: BackgroundAISettingsDTO, viewModel: SettingsViewModel) {
        self.settings = settings
        self.viewModel = viewModel
        _enabled = State(initialValue: settings.enabled)
        _tasks = State(initialValue: Set(settings.tasks))
    }

    var body: some View {
        Toggle("Run automatically", isOn: $enabled)
        ForEach(options, id: \.0) { key, label in
            Toggle(label, isOn: Binding(
                get: { tasks.contains(key) },
                set: { value in
                    if value { tasks.insert(key) } else { tasks.remove(key) }
                }
            ))
        }
        Button("Save Background AI") {
            Task { await viewModel.saveBackgroundAI(enabled: enabled, tasks: Array(tasks).sorted()) }
        }
        .accessibilityIdentifier("kos.settings.backgroundSave")
    }
}

private struct PromptOverrideEditor: View {
    let prompt: PromptDTO
    let viewModel: SettingsViewModel
    @State private var template: String

    init(prompt: PromptDTO, viewModel: SettingsViewModel) {
        self.prompt = prompt
        self.viewModel = viewModel
        _template = State(initialValue: prompt.effectiveTemplate)
    }

    var body: some View {
        Form {
            Section("Template") {
                TextEditor(text: $template)
                    .font(.system(.body, design: .monospaced))
                    .frame(minHeight: 240)
                    .accessibilityIdentifier("kos.settings.promptEditor")
            }
            Section("Variables") {
                if prompt.variables.isEmpty {
                    Text("None")
                } else {
                    ForEach(prompt.variables, id: \.self) { variable in
                        Text("{\(variable)}")
                    }
                }
            }
            Section {
                Button("Save") {
                    Task { await viewModel.savePrompt(prompt, template: template) }
                }
                .accessibilityIdentifier("kos.settings.promptSave")
                Button("Reset to Default") {
                    Task {
                        await viewModel.resetPrompt(prompt)
                        template = prompt.defaultTemplate
                    }
                }
                .accessibilityIdentifier("kos.settings.promptReset")
            }
        }
        .navigationTitle(prompt.displayName)
        .navigationBarTitleDisplayMode(.inline)
    }
}
