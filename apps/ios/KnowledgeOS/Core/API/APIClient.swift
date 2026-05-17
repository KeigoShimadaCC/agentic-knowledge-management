import Foundation
import os.log

protocol APIClientProtocol: Sendable {
    func request<T: Decodable>(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> T
    func requestData(_ endpoint: APIEndpoint, body: (any Encodable)?, auth: Bool) async throws -> Data
    func uploadMultipart(_ endpoint: APIEndpoint, upload: MultipartUpload, auth: Bool) async throws -> Data
    var bearerToken: String? { get }
    func setBearerToken(_ token: String?)
    func setUnauthorizedHandler(_ handler: (@Sendable () async -> Void)?)
}

final class APIClient: APIClientProtocol, @unchecked Sendable {
    private let serverConfig: ServerConfig
    private let session: URLSession
    private let networkMonitor: NetworkMonitor?
    private let lock = NSLock()
    private var token: String?
    private var unauthorizedHandler: (@Sendable () async -> Void)?

    private static let logger = Logger(subsystem: "com.knowledgeos.ios", category: "APIClient")

    init(
        serverConfig: ServerConfig = .shared,
        session: URLSession = .shared,
        networkMonitor: NetworkMonitor? = nil
    ) {
        self.serverConfig = serverConfig
        self.session = session
        self.networkMonitor = networkMonitor
    }

    var bearerToken: String? {
        lock.lock()
        defer { lock.unlock() }
        return token
    }

    func setBearerToken(_ token: String?) {
        lock.lock()
        defer { lock.unlock() }
        self.token = token
    }

    func setUnauthorizedHandler(_ handler: (@Sendable () async -> Void)?) {
        lock.lock()
        defer { lock.unlock() }
        unauthorizedHandler = handler
    }

    func request<T: Decodable>(
        _ endpoint: APIEndpoint,
        body: (any Encodable)? = nil,
        auth: Bool = true
    ) async throws -> T {
        let data = try await requestData(endpoint, body: body, auth: auth)
        do {
            return try JSONCoding.decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingFailed(error.localizedDescription)
        }
    }

    func requestData(
        _ endpoint: APIEndpoint,
        body: (any Encodable)? = nil,
        auth: Bool = true
    ) async throws -> Data {
        if let networkMonitor {
            let reachable = await MainActor.run { networkMonitor.isReachable }
            if !reachable {
                throw APIError.networkUnavailable
            }
        }

        let request = try makeRequest(endpoint: endpoint, body: body, auth: auth, contentType: "application/json")
        return try await perform(request: request, endpoint: endpoint)
    }

    func uploadMultipart(
        _ endpoint: APIEndpoint,
        upload: MultipartUpload,
        auth: Bool = true
    ) async throws -> Data {
        if let networkMonitor {
            let reachable = await MainActor.run { networkMonitor.isReachable }
            if !reachable {
                throw APIError.networkUnavailable
            }
        }

        var request = try makeRequest(endpoint: endpoint, body: nil, auth: auth, contentType: upload.contentType)
        request.httpBody = upload.body
        return try await perform(request: request, endpoint: endpoint)
    }

    func getHealth() async throws -> HealthResponse {
        try await request(.health, body: nil as String?, auth: false)
    }

    private func makeRequest(
        endpoint: APIEndpoint,
        body: (any Encodable)?,
        auth: Bool,
        contentType: String
    ) throws -> URLRequest {
        let base = serverConfig.baseURL
        guard let url = URL(string: endpoint.relativePath, relativeTo: base) else {
            throw APIError.validation("Invalid API URL.")
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.timeoutInterval = 30
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if auth, let token = bearerToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body {
            request.httpBody = try JSONCoding.encoder.encode(AnyEncodable(body))
        }

        return request
    }

    private func perform(request: URLRequest, endpoint: APIEndpoint) async throws -> Data {
        let path = request.url?.path ?? endpoint.path
        let method = request.httpMethod ?? endpoint.method.rawValue

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            Self.logger.error("\(method, privacy: .public) \(path, privacy: .public) network error")
            throw APIError.networkUnavailable
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.serverError
        }

        Self.logger.info("\(method, privacy: .public) \(path, privacy: .public) status=\(http.statusCode, privacy: .public)")

        if http.statusCode == 401 {
            let handler = lock.withLock { unauthorizedHandler }
            if let handler {
                await handler()
            }
            throw APIError.notAuthenticated
        }

        guard (200..<300).contains(http.statusCode) else {
            throw APIError.from(httpStatus: http.statusCode, data: data)
        }

        return data
    }
}

/// Type-erased Encodable wrapper for generic request bodies.
private struct AnyEncodable: Encodable {
    private let encode: (Encoder) throws -> Void

    init(_ wrapped: any Encodable) {
        encode = wrapped.encode
    }

    func encode(to encoder: Encoder) throws {
        try encode(encoder)
    }
}

private extension NSLock {
    func withLock<T>(_ body: () -> T) -> T {
        lock()
        defer { unlock() }
        return body()
    }
}
