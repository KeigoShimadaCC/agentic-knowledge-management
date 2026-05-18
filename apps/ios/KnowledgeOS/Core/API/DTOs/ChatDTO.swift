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

struct ChatSummaryDateRangeDTO: Codable, Equatable {
    let start: String?
    let end: String?
}

struct ChatSummaryReferencedItemDTO: Codable, Equatable {
    let turnRefs: [Int]
    let confidence: String
}

struct ChatSummaryKeyDecisionDTO: Codable, Equatable {
    let decision: String
    let rationale: String?
    let turnRefs: [Int]
    let confidence: String
}

struct ChatSummaryOpenQuestionDTO: Codable, Equatable {
    let question: String
    let status: String
    let turnRefs: [Int]
    let confidence: String
}

struct ChatSummaryActionItemDTO: Codable, Equatable {
    let task: String
    let owner: String?
    let dueAt: String?
    let turnRefs: [Int]
    let confidence: String
}

struct ChatSummaryClaimDTO: Codable, Equatable {
    let claim: String
    let type: String
    let turnRefs: [Int]
    let confidence: String
}

struct ChatSummaryConceptDTO: Codable, Equatable {
    let name: String
    let type: String
    let turnRefs: [Int]
    let confidence: String
}

struct ChatSummarySuggestedLinkDTO: Codable, Equatable, Identifiable {
    var id: String { "\(targetObjectId?.uuidString ?? targetTitle)-\(edgeKind)" }
    let targetObjectId: UUID?
    let targetTitle: String
    let edgeKind: String
    let rationale: String
    let confidence: String
}

struct StructuredChatSummaryDTO: Codable, Equatable {
    let title: String
    let summary: String
    let dateRange: ChatSummaryDateRangeDTO?
    let topics: [String]
    let keyDecisions: [ChatSummaryKeyDecisionDTO]
    let openQuestions: [ChatSummaryOpenQuestionDTO]
    let actionItems: [ChatSummaryActionItemDTO]
    let claims: [ChatSummaryClaimDTO]
    let concepts: [ChatSummaryConceptDTO]
    let suggestedLinks: [ChatSummarySuggestedLinkDTO]
    let warnings: [String]
}

struct StructuredSummaryPreviewDTO: Codable, Equatable {
    let structuredSummary: StructuredChatSummaryDTO
    let agentRunId: UUID
    let status: String
}
