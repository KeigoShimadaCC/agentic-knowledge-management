import SwiftUI

struct TagChipEditor: View {
    @Binding var tags: [String]
    @State private var draft: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !tags.isEmpty {
                FlowLayout(spacing: 6) {
                    ForEach(tags, id: \.self) { tag in
                        TagChip(label: tag) {
                            remove(tag)
                        }
                    }
                }
            }

            HStack(spacing: 8) {
                TextField("Add tag", text: $draft)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled(true)
                    .submitLabel(.done)
                    .onSubmit { commitDraft() }
                    .onChange(of: draft) { _, newValue in
                        if newValue.contains(",") {
                            commitDraft()
                        }
                    }
                    .accessibilityIdentifier(Kos.EditMetadata.tagField)

                Button("Add") { commitDraft() }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .disabled(normalized(draft).isEmpty)
                    .accessibilityIdentifier(Kos.EditMetadata.tagAddButton)
            }
        }
    }

    private func commitDraft() {
        let candidate = normalized(draft)
        defer { draft = "" }
        guard !candidate.isEmpty else { return }
        let alreadyPresent = tags.contains { $0.lowercased() == candidate.lowercased() }
        guard !alreadyPresent else { return }
        tags.append(candidate)
    }

    private func remove(_ tag: String) {
        tags.removeAll { $0 == tag }
    }

    private func normalized(_ raw: String) -> String {
        raw
            .replacingOccurrences(of: ",", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

private struct TagChip: View {
    let label: String
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 4) {
            Text(label)
                .font(.footnote)
                .lineLimit(1)
            Button(action: onRemove) {
                Image(systemName: "xmark.circle.fill")
                    .font(.caption)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Remove tag \(label)")
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.secondary.opacity(0.15), in: Capsule())
        .accessibilityIdentifier(Kos.EditMetadata.tagChip)
    }
}

/// Minimal flow layout for chips. Wraps children across lines.
private struct FlowLayout: Layout {
    let spacing: CGFloat

    init(spacing: CGFloat = 8) {
        self.spacing = spacing
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        let rows = layout(subviews: subviews, in: maxWidth)
        let height = rows.reduce(0) { $0 + $1.height } + spacing * CGFloat(max(0, rows.count - 1))
        let width = rows.map(\.width).max() ?? 0
        return CGSize(width: width, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let rows = layout(subviews: subviews, in: bounds.width)
        var y = bounds.minY
        for row in rows {
            var x = bounds.minX
            for item in row.items {
                let size = item.size
                item.view.place(
                    at: CGPoint(x: x, y: y),
                    proposal: ProposedViewSize(size)
                )
                x += size.width + spacing
            }
            y += row.height + spacing
        }
    }

    private struct Row {
        var items: [(view: LayoutSubview, size: CGSize)] = []
        var width: CGFloat = 0
        var height: CGFloat = 0
    }

    private func layout(subviews: Subviews, in maxWidth: CGFloat) -> [Row] {
        var rows: [Row] = [Row()]
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            let needsBreak = !rows[rows.count - 1].items.isEmpty
                && rows[rows.count - 1].width + spacing + size.width > maxWidth
            if needsBreak {
                rows.append(Row())
            }
            var current = rows[rows.count - 1]
            if !current.items.isEmpty {
                current.width += spacing
            }
            current.items.append((subview, size))
            current.width += size.width
            current.height = max(current.height, size.height)
            rows[rows.count - 1] = current
        }
        return rows
    }
}
