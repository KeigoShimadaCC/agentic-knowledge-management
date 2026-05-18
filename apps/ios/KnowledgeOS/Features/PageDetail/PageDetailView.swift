import SwiftUI

struct PageDetailView: View {
    let object: ObjectDTO
    @State private var viewModel = PageDetailViewModel()
    @State private var isEditingBody = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                DetailHeader(object: object)
                AIActionsBar(object: object)

                if viewModel.isLoading {
                    LoadingView(message: "Loading page...")
                        .frame(minHeight: 240)
                } else if let message = viewModel.errorMessage {
                    ErrorView(title: "Could not load page", message: message) {
                        Task { await viewModel.load(id: object.id) }
                    }
                } else if let page = viewModel.page {
                    TiptapDocumentView(content: page.contentJson)
                } else {
                    EmptyStateView(title: "Empty page", message: "This page has no readable content.")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    isEditingBody = true
                } label: {
                    Label("Edit body", systemImage: "square.and.pencil")
                }
                .disabled(viewModel.page == nil)
                .accessibilityIdentifier(Kos.PageDetail.editButton)
            }
        }
        .sheet(isPresented: $isEditingBody) {
            if let page = viewModel.page {
                EditBodySheet(
                    page: page,
                    objectTitle: object.title,
                    onSaved: { updated in viewModel.apply(updated: updated) },
                    onConflict: { conflict in viewModel.conflict = conflict }
                )
            }
        }
        .sheet(item: Binding(
            get: { viewModel.conflict },
            set: { viewModel.conflict = $0 }
        )) { conflict in
            ConflictResolutionSheet(
                conflict: conflict,
                onDiscard: { await viewModel.discardAndRefresh(pageID: conflict.pageID) },
                onKeepMine: {
                    await viewModel.overwriteWith(draftText: conflict.draftText, pageID: conflict.pageID)
                }
            )
        }
        .task {
            await viewModel.load(id: object.id)
        }
    }
}

struct DetailHeader: View {
    let object: ObjectDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ObjectKindBadge(kind: object.kind)
            Text(object.title)
                .font(.title2.weight(.semibold))
            if let description = object.description, !description.isEmpty {
                Text(description)
                    .foregroundStyle(.secondary)
            }
            if !object.tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(object.tags, id: \.self) { tag in
                            Text(tag)
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(Color.secondary.opacity(0.15), in: Capsule())
                        }
                    }
                }
                .accessibilityIdentifier(Kos.ObjectDetail.tagsRow)
            }
        }
    }
}

private struct TiptapDocumentView: View {
    let content: [String: AnyCodable]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(TiptapNode.documentNodes(from: content)) { node in
                TiptapNodeView(node: node)
            }
        }
    }
}

private struct TiptapNode: Identifiable {
    let id = UUID()
    let type: String
    let text: String
    let level: Int?
    let children: [TiptapNode]

    static func documentNodes(from content: [String: AnyCodable]) -> [TiptapNode] {
        guard let raw = content["content"]?.value as? [[String: Any]] else { return [] }
        return raw.map(parse)
    }

    private static func parse(_ raw: [String: Any]) -> TiptapNode {
        let type = raw["type"] as? String ?? "unsupported"
        let attrs = raw["attrs"] as? [String: Any]
        let children = (raw["content"] as? [[String: Any]] ?? []).map(parse)
        return TiptapNode(
            type: type,
            text: collectText(from: raw),
            level: attrs?["level"] as? Int,
            children: children
        )
    }

    private static func collectText(from raw: [String: Any]) -> String {
        if let text = raw["text"] as? String { return text }
        return (raw["content"] as? [[String: Any]] ?? []).map(collectText).joined()
    }
}

private struct TiptapNodeView: View {
    let node: TiptapNode

    var body: some View {
        switch node.type {
        case "paragraph":
            if !node.text.isEmpty {
                Text(node.text)
                    .font(.body)
            }
        case "heading":
            Text(node.text)
                .font(headingFont(level: node.level ?? 2))
                .fontWeight(.semibold)
        case "bulletList":
            VStack(alignment: .leading, spacing: 8) {
                ForEach(node.children) { child in
                    Label(child.text, systemImage: "circle.fill")
                        .font(.body)
                }
            }
        case "orderedList":
            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(node.children.enumerated()), id: \.element.id) { index, child in
                    Text("\(index + 1). \(child.text)")
                }
            }
        case "blockquote":
            Text(node.text)
                .foregroundStyle(.secondary)
                .padding(.leading, 12)
                .overlay(alignment: .leading) {
                    Rectangle().fill(.secondary.opacity(0.4)).frame(width: 3)
                }
        case "codeBlock":
            Text(node.text)
                .font(.system(.body, design: .monospaced))
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(.gray.opacity(0.14), in: RoundedRectangle(cornerRadius: 8))
        default:
            Text("Unsupported block")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.vertical, 6)
        }
    }

    private func headingFont(level: Int) -> Font {
        switch level {
        case 1: return .title2
        case 2: return .title3
        default: return .headline
        }
    }
}
