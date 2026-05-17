import Foundation

struct AssetDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let filename: String
    let contentType: String
    let sizeBytes: Int
    let sha256: String
    let storagePath: String
    let status: String
    let width: Int?
    let height: Int?
    let durationSecs: Double?
    let createdAt: Date
    let updatedAt: Date
}

struct AssetUploadResponseDTO: Decodable {
    let object: ObjectDTO
    let asset: AssetDTO
}
