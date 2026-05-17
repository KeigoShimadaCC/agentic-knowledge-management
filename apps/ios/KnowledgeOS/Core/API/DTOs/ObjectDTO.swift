import Foundation

struct ObjectDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let kind: String
    let title: String
    let description: String?
    let tags: [String]
    let metadata: [String: AnyCodable]?
    let isPinned: Bool
    let isArchived: Bool
    let aiGenerated: Bool
    let createdAt: Date
    let updatedAt: Date
    let deletedAt: Date?
}

struct IndexStatusDTO: Codable, Equatable {
    let objectId: UUID
    let totalChunks: Int
    let embeddedCount: Int
    let status: String
    let lastEmbeddedAt: Date?
}
