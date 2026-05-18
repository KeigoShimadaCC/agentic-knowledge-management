import Foundation

struct PaginatedResponseDTO<T: Codable>: Codable {
    let items: [T]
    let total: Int
    let page: Int
    let limit: Int
    let pages: Int
}
