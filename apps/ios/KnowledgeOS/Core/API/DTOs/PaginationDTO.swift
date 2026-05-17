import Foundation

struct PaginatedResponseDTO<T: Decodable>: Decodable {
    let items: [T]
    let total: Int
    let page: Int
    let limit: Int
    let pages: Int
}
