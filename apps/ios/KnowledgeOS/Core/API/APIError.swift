import Foundation

struct APIErrorEnvelope: Decodable {
    let detail: String
    let code: String?
}

enum APIError: Error, Equatable {
    case notAuthenticated
    case forbidden
    case notFound
    case validation(String)
    case serverError
    case aiDisabled
    case networkUnavailable
    case decodingFailed(String)

    var userMessage: String {
        switch self {
        case .notAuthenticated:
            return "Please sign in again."
        case .forbidden:
            return "You do not have permission to perform this action."
        case .notFound:
            return "The requested item was not found."
        case let .validation(detail):
            return detail
        case .serverError:
            return "The server encountered an error. Try again later."
        case .aiDisabled:
            return "AI features are disabled on this server."
        case .networkUnavailable:
            return "No network connection. Check your connection and try again."
        case let .decodingFailed(message):
            return "Could not read the server response. (\(message))"
        }
    }

    static func from(httpStatus: Int, data: Data?) -> APIError {
        let envelope = data.flatMap { try? JSONCoding.decoder.decode(APIErrorEnvelope.self, from: $0) }
        let detail = envelope?.detail ?? "Request failed"
        let code = envelope?.code?.lowercased() ?? ""

        switch httpStatus {
        case 401:
            return .notAuthenticated
        case 403:
            return .forbidden
        case 404:
            return .notFound
        case 400, 422:
            return .validation(detail)
        case 503 where code == "ai_disabled":
            return .aiDisabled
        case 500...599:
            return .serverError
        default:
            if code == "ai_disabled" {
                return .aiDisabled
            }
            return .validation(detail)
        }
    }
}
