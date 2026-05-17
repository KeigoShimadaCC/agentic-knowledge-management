import Foundation

struct UserDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let email: String
    let displayName: String
    let createdAt: Date?
}
