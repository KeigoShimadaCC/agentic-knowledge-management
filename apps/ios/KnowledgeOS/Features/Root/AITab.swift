import SwiftUI

struct AITab: View {
    var body: some View {
        NavigationStack {
            EmptyStateView(
                title: "AI",
                message: "KB Q&A arrives in PHONE-03C."
            )
            .navigationTitle("AI")
        }
        .accessibilityIdentifier("ai.tab")
    }
}
