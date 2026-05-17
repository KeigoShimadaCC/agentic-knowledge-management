import Foundation

struct AnswerRequest: Encodable {
    let q: String
    let kind: String?
    let limit: Int
    let objectIds: [UUID]?
    let useWebSearch: Bool
}

struct CitationDTO: Codable, Equatable {
    let objectId: UUID
    let title: String
    let kind: String
    let snippet: String?
}

struct WebCitationDTO: Codable, Equatable {
    let title: String
    let url: String
    let snippet: String?
}

struct AnswerResponseDTO: Decodable {
    let answer: String
    let citations: [CitationDTO]
    let agentRunId: UUID
    let contextCount: Int
    let webCitations: [WebCitationDTO]
    let warning: String?
}

struct SummarizeRequest: Encodable {
    let objectId: UUID
    let force: Bool
}

struct SummarizeResponseDTO: Decodable {
    let summary: String
    let agentRunId: UUID
    let cached: Bool
}

struct SuggestLinksRequest: Encodable {
    let objectId: UUID
    let limit: Int
}

struct LinkSuggestionDTO: Codable, Equatable {
    let targetId: UUID
    let targetTitle: String
    let targetKind: String
    let reason: String
    let confidence: Double
}

struct SuggestLinksResponseDTO: Decodable {
    let suggestions: [LinkSuggestionDTO]
    let agentRunId: UUID
}
