import SwiftUI

struct SettingsTab: View {
    @Environment(AuthStore.self) private var authStore
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
                    Section("Capabilities") {
                        LabeledContent("AI", value: capabilities.aiEnabled ? "On" : "Off")
                        LabeledContent("Embeddings", value: capabilities.embeddingsEnabled ? "On" : "Off")
                        LabeledContent("Upload", value: capabilities.uploadEnabled ? "On" : "Off")
                    }
                }

            }
            .navigationTitle("Settings")
            .accessibilityIdentifier("settings.tab")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Sign Out", role: .destructive) {
                        onLogout()
                    }
                    .accessibilityIdentifier("settings.logout")
                }
            }
        }
    }
}
