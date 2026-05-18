import Foundation

struct ObjectUpdateRequest: Encodable {
    let title: String?
    let description: String?
    let tags: [String]?
}

struct EdgeCreateRequest: Encodable {
    let sourceId: UUID
    let targetId: UUID
    let kind: String
    let weight: Double
    let metadata: [String: AnyCodable]
}

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

struct ObjectSummaryDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let kind: String
    let title: String
    let description: String?
    let tags: [String]
    let deletedAt: Date?
}

struct EdgeDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let sourceId: UUID
    let targetId: UUID
    let kind: String
    let weight: Double
    let metadata: [String: AnyCodable]
    let createdAt: Date
    let deletedAt: Date?
    let source: ObjectSummaryDTO
    let target: ObjectSummaryDTO
    let direction: String?
}

struct EdgeMutationDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let sourceId: UUID
    let targetId: UUID
    let kind: String
    let weight: Double
    let metadata: [String: AnyCodable]
    let createdAt: Date
    let deletedAt: Date?
}

struct RelatedObjectDTO: Codable, Equatable, Identifiable {
    let object: ObjectSummaryDTO
    let distance: Int
    let score: Double
    let viaEdges: [EdgeDTO]

    var id: UUID { object.id }
}
