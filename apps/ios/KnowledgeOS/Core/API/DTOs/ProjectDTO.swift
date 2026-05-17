import Foundation

struct ProjectDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let title: String
    let description: String?
    let periodStart: String?
    let periodEnd: String?
    let role: String?
    let organization: String?
    let problem: String?
    let actions: String?
    let results: String?
    let metrics: [String: AnyCodable]?
    let skills: [String]
    let status: String
    let tags: [String]
    let isPinned: Bool
    let isArchived: Bool
    let confidence: String
    let extractedFrom: UUID?
    let extractedByAgentRunId: UUID?
    let createdAt: Date
    let updatedAt: Date
    let deletedAt: Date?
}
