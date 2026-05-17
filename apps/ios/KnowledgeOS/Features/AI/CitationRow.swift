import SwiftUI

struct CitationRow: View {
    let citation: CitationDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                ObjectKindBadge(kind: citation.kind)
                Spacer()
            }
            Text(citation.title)
                .font(.subheadline)
                .lineLimit(2)
            if let snippet = citation.snippet, !snippet.isEmpty {
                Text(snippet)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }
        }
        .padding(.vertical, 4)
        .accessibilityIdentifier("kos.ai.citationRow")
    }
}
