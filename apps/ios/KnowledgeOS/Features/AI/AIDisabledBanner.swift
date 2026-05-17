import SwiftUI

struct AIDisabledBanner: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                Text("AI features are disabled")
                    .font(.subheadline.weight(.semibold))
            }
            Text("Set OPENAI_API_KEY in infra/.env on the host KnowledgeOS server and restart the API to enable.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
        .accessibilityIdentifier("kos.ai.disabledBanner")
    }
}
