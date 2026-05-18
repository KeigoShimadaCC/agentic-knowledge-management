import XCTest
@testable import KnowledgeOS

final class TiptapPlainTextTests: XCTestCase {
    func testEmptyInputProducesEmptyDoc() {
        let doc = TiptapPlainText.tiptapDocument(from: "")
        XCTAssertEqual(doc["type"]?.value as? String, "doc")
        let content = doc["content"]?.value as? [Any] ?? []
        XCTAssertTrue(content.isEmpty)
    }

    func testWhitespaceOnlyInputProducesEmptyDoc() {
        let doc = TiptapPlainText.tiptapDocument(from: "   \n\n  \t  ")
        let content = doc["content"]?.value as? [Any] ?? []
        XCTAssertTrue(content.isEmpty)
    }

    func testSingleLineWrapsOneParagraph() throws {
        let doc = TiptapPlainText.tiptapDocument(from: "hello world")
        let content = try XCTUnwrap(doc["content"]?.value as? [[String: Any]])
        XCTAssertEqual(content.count, 1)
        XCTAssertEqual(content[0]["type"] as? String, "paragraph")
        let textNodes = content[0]["content"] as? [[String: Any]] ?? []
        XCTAssertEqual(textNodes.first?["text"] as? String, "hello world")
    }

    func testMultipleLinesAndBlanksProduceParagraphPerNonEmptyLine() throws {
        let doc = TiptapPlainText.tiptapDocument(from: "First\n\nSecond\n\n\nThird")
        let content = try XCTUnwrap(doc["content"]?.value as? [[String: Any]])
        XCTAssertEqual(content.count, 3)
        XCTAssertEqual(
            content.compactMap { ($0["content"] as? [[String: Any]])?.first?["text"] as? String },
            ["First", "Second", "Third"]
        )
    }

    func testRoundTripPreservesNonEmptyLines() {
        let original = "alpha\nbeta\ngamma"
        let doc = TiptapPlainText.tiptapDocument(from: original)
        let extracted = TiptapPlainText.extractPlainText(from: doc)
        XCTAssertEqual(extracted, original)
    }

    func testExtractPlainTextFromDocWithoutContent() {
        let extracted = TiptapPlainText.extractPlainText(from: ["type": AnyCodable("doc")])
        XCTAssertEqual(extracted, "")
    }

    func testExtractPlainTextFlattensNestedTextNodes() {
        let doc: [String: AnyCodable] = [
            "type": AnyCodable("doc"),
            "content": AnyCodable([
                [
                    "type": "paragraph",
                    "content": [
                        ["type": "text", "text": "hello "],
                        ["type": "text", "text": "world"],
                    ],
                ],
            ]),
        ]
        XCTAssertEqual(TiptapPlainText.extractPlainText(from: doc), "hello world")
    }
}
