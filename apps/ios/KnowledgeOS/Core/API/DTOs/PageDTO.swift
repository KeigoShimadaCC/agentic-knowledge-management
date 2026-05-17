import Foundation

struct PageCreateRequest: Encodable {
    let title: String
    let contentJson: [String: AnyCodable]
}

struct PageUpdateRequest: Encodable {
    let title: String?
    let contentJson: [String: AnyCodable]?
    let contentText: String?
    let expectedVersion: Int?
}

struct PageDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let contentJson: [String: AnyCodable]
    let contentText: String
    let wordCount: Int
    let version: Int
    let createdAt: Date
    let updatedAt: Date
}
