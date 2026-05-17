import Foundation

struct SourceDTO: Codable, Equatable, Identifiable {
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
    let sourceType: String
    let url: String?
    let assetId: UUID?
    let ingestionStatus: String
    let extractedText: String?
    let pageCount: Int?
    let thumbnailPath: String?
    let previewData: [String: AnyCodable]?
    let errorMessage: String?
}
