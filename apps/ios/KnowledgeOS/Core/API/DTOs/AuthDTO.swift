import Foundation

struct UserDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let email: String
    let displayName: String
    let createdAt: Date?
}

struct MobileCapabilitiesDTO: Codable, Equatable {
    let aiEnabled: Bool
    let embeddingsEnabled: Bool
    let uploadEnabled: Bool
    let mobileApiVersion: Int
}

struct MobileLoginRequest: Encodable {
    let email: String
    let password: String
    let deviceName: String?
}

struct MobileLoginResponse: Decodable {
    let token: String
    let user: UserDTO
    let expiresAt: Date
}

struct MobileBootstrapResponse: Decodable {
    let user: UserDTO
    let capabilities: MobileCapabilitiesDTO
}

struct OkResponse: Decodable {
    let ok: Bool
}
