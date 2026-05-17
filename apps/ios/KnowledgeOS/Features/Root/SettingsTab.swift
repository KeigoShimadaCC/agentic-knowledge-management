import SwiftUI

struct SettingsTab: View {
    @Environment(AuthStore.self) private var authStore
    @EnvironmentObject private var appState: AppState
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

            }
            .navigationTitle("Settings")
            .accessibilityIdentifier("kos.settings.screen")
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
}
