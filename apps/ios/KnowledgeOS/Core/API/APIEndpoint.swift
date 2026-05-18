import Foundation

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case patch = "PATCH"
    case delete = "DELETE"
}

struct APIEndpoint {
    let path: String
    let method: HTTPMethod
    var queryItems: [URLQueryItem] = []

    var relativePath: String {
        if queryItems.isEmpty {
            return path
        }
        var components = URLComponents()
        components.queryItems = queryItems
        let query = components.percentEncodedQuery.map { "?\($0)" } ?? ""
        return path + query
    }

    static let health = APIEndpoint(path: "/api/v1/health", method: .get)
    static let mobileLogin = APIEndpoint(path: "/api/v1/auth/mobile-login", method: .post)
    static let mobileLogout = APIEndpoint(path: "/api/v1/auth/mobile-logout", method: .post)
    static let mobileBootstrap = APIEndpoint(path: "/api/v1/mobile/bootstrap", method: .get)
    static let authMe = APIEndpoint(path: "/api/v1/auth/me", method: .get)

    static func objects(page: Int = 1, limit: Int = 25, kind: String? = nil, q: String? = nil) -> APIEndpoint {
        var items = [
            URLQueryItem(name: "page", value: String(page)),
            URLQueryItem(name: "limit", value: String(limit)),
        ]
        if let kind { items.append(URLQueryItem(name: "kind", value: kind)) }
        if let q { items.append(URLQueryItem(name: "q", value: q)) }
        return APIEndpoint(path: "/api/v1/objects", method: .get, queryItems: items)
    }

    static func object(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/objects/\(id.uuidString)", method: .get)
    }

    static func updateObject(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/objects/\(id.uuidString)", method: .patch)
    }

    static func page(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/pages/\(id.uuidString)", method: .get)
    }

    static func updatePage(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/pages/\(id.uuidString)", method: .put)
    }

    static let createPage = APIEndpoint(path: "/api/v1/pages", method: .post)

    static func source(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/sources/\(id.uuidString)", method: .get)
    }

    static func assetMeta(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/assets/\(id.uuidString)", method: .get)
    }

    static func assetDownload(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/assets/\(id.uuidString)/download", method: .get)
    }

    static func assetUpload(createSource: Bool = false) -> APIEndpoint {
        APIEndpoint(
            path: "/api/v1/assets/upload",
            method: .post,
            queryItems: createSource ? [URLQueryItem(name: "create_source", value: "true")] : []
        )
    }

    static func chat(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/chats/\(id.uuidString)", method: .get)
    }

    static func project(id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/projects/\(id.uuidString)", method: .get)
    }

    static let hybridSearch = APIEndpoint(path: "/api/v1/search/hybrid", method: .post)
    static let aiAnswer = APIEndpoint(path: "/api/v1/ai/answer", method: .post)
    static let aiSummarize = APIEndpoint(path: "/api/v1/ai/summarize", method: .post)
    static let aiSuggestLinks = APIEndpoint(path: "/api/v1/ai/suggest-links", method: .post)
    static let settings = APIEndpoint(path: "/api/v1/settings", method: .get)
    static let settingsSecrets = APIEndpoint(path: "/api/v1/settings/secrets", method: .patch)
    static let mcpConnections = APIEndpoint(path: "/api/v1/mcp-connections/", method: .get)
    static let settingsBackgroundAI = APIEndpoint(path: "/api/v1/settings/background-ai", method: .patch)

    static func settingsFeature(_ key: String) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/settings/ai-features/\(key)", method: .patch)
    }

    static func settingsPrompt(_ key: String) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/settings/prompts/\(key)", method: .patch)
    }

    static func settingsPromptReset(_ key: String) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/settings/prompts/\(key)/reset", method: .post)
    }

    static func mcpConnection(_ id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/mcp-connections/\(id.uuidString)", method: .patch)
    }

    static func mcpConnectionTest(_ id: UUID) -> APIEndpoint {
        APIEndpoint(path: "/api/v1/mcp-connections/\(id.uuidString)/test", method: .post)
    }
}
