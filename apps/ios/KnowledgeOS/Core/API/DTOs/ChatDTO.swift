import Foundation

struct ChatTurnDTO: Codable, Equatable {
    let turnIndex: Int
    let role: String
    let author: String?
    let content: String
    let createdAt: String?
    let metadata: [String: AnyCodable]?
}

struct ChatDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let kind: String
    let title: String
    let description: String?
    let tags: [String]
    let isPinned: Bool
    let isArchived: Bool
    let createdAt: Date
    let updatedAt: Date
    let deletedAt: Date?
    let provider: String
    let externalChatId: String?
    let sourceFilename: String?
    let rawStoragePath: String
    let rawFormat: String
    let turnCount: Int
    let startedAt: Date?
    let endedAt: Date?
    let importedAt: Date
    let parsedTurns: [ChatTurnDTO]
    let contentText: String
    let metadata: [String: AnyCodable]?
    let structuredSummary: [String: AnyCodable]?
    let structuredSummaryStatus: String
    let structuredSummaryAgentRunId: UUID?
    let structuredSummaryUpdatedAt: Date?
}
