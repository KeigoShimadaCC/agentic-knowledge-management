import Foundation

struct WorkspaceUpdateRequest: Encodable {
    let name: String?
    let description: String?
    let layout: WorkspaceLayoutDTO?
    let isPinned: Bool?
}

struct WorkspacePaneDTO: Codable, Equatable {
    let id: String
    let objectId: UUID?
    let objectKind: String?
    let sizePct: Int
    let mode: String
}

struct WorkspaceLayoutDTO: Codable, Equatable {
    let version: Int
    let split: String?
    let panes: [WorkspacePaneDTO]
    let activePaneId: String
}

struct WorkspaceDTO: Codable, Equatable, Identifiable {
    let id: UUID
    let userId: UUID
    let name: String
    let description: String?
    let layout: WorkspaceLayoutDTO
    let isPinned: Bool
    let lastUsedAt: Date?
    let createdAt: Date
    let updatedAt: Date
    let deletedAt: Date?
}
