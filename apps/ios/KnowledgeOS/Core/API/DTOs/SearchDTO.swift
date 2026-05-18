import Foundation

struct SearchSnippetDTO: Codable, Equatable {
    let text: String
    let highlights: [[Int]]
}

struct HybridSearchRequest: Encodable {
    let q: String
    let kind: String?
    let sourceType: String?
    let limit: Int
    let debug: Bool
    let objectIds: [UUID]?
}

struct HybridSearchResultDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let kind: String
    let title: String
    let snippet: SearchSnippetDTO?
    let tags: [String]
    let score: Double
    let updatedAt: Date
    let sourceType: String?
    let ingestionStatus: String?
    let keywordScore: Double
    let vectorScore: Double
    let recencyBoost: Double
}

struct HybridSearchResponseDTO: Codable {
    let results: [HybridSearchResultDTO]
    let total: Int
    let query: String
    let mode: String
    let embeddingsUsed: Bool
}
