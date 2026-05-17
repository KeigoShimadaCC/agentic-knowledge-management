import Foundation

/// Pure functions to convert between plain text and the Tiptap `doc` JSON shape.
/// The backend's `content_json` validator expects a top-level `{"type":"doc","content":[…]}`.
enum TiptapPlainText {
    /// Splits plain text on newlines, drops empty lines, and wraps each surviving
    /// line as a `paragraph` node containing one `text` node. Empty input yields
    /// `{"type":"doc","content":[]}`.
    static func tiptapDocument(from plain: String) -> [String: AnyCodable] {
        let paragraphs = plain
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        let content: [[String: Any]] = paragraphs.map { paragraph in
            [
                "type": "paragraph",
                "content": [
                    [
                        "type": "text",
                        "text": paragraph,
                    ],
                ],
            ]
        }

        return [
            "type": AnyCodable("doc"),
            "content": AnyCodable(content),
        ]
    }

    /// Extracts plain text from a Tiptap doc by concatenating text nodes within
    /// paragraph/heading blocks, separated by `\n`. Used to pre-fill the editor.
    static func extractPlainText(from doc: [String: AnyCodable]) -> String {
        guard let raw = doc["content"]?.value as? [[String: Any]] else { return "" }
        return raw.map(extractBlockText).joined(separator: "\n")
    }

    private static func extractBlockText(_ raw: [String: Any]) -> String {
        if let text = raw["text"] as? String { return text }
        let children = raw["content"] as? [[String: Any]] ?? []
        return children.map(extractBlockText).joined()
    }
}
