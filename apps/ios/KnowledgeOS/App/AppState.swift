import Foundation

@MainActor
final class AppState: ObservableObject {
    enum ConnectionState: Equatable {
        case disconnected
        case checking
        case connected
        case failed(String)
    }

    @Published var baseURLString: String
    @Published var connectionState: ConnectionState = .disconnected
    @Published var isSessionAuthenticated = false

    var onBaseURLWillChange: ((String, String) -> Void)?

    private let serverConfig: ServerConfig

    init(serverConfig: ServerConfig = .shared) {
        self.serverConfig = serverConfig
        self.baseURLString = serverConfig.baseURL.absoluteString
        if serverConfig.hasPersistedBaseURL {
            connectionState = .connected
        }
    }

    var isConnected: Bool {
        connectionState == .connected
    }

    func updateBaseURL(_ text: String) {
        let oldURL = serverConfig.baseURL.absoluteString
        baseURLString = text
        connectionState = .disconnected
        if let url = Self.parseBaseURL(text) {
            let newURL = url.normalizedBaseURL.absoluteString
            if oldURL != newURL {
                onBaseURLWillChange?(oldURL, newURL)
            }
        }
    }

    func markChecking() {
        connectionState = .checking
    }

    func markConnected(baseURL: URL) {
        let oldURL = serverConfig.baseURL.absoluteString
        let normalized = baseURL.normalizedBaseURL
        let newURL = normalized.absoluteString
        if oldURL != newURL {
            onBaseURLWillChange?(oldURL, newURL)
        }
        serverConfig.saveBaseURL(normalized)
        baseURLString = newURL
        connectionState = .connected
    }

    func markFailed(_ message: String) {
        connectionState = .failed(message)
    }

    private static func parseBaseURL(_ text: String) -> URL? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed),
              let scheme = url.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              url.host != nil else {
            return nil
        }
        return url.normalizedBaseURL
    }
}
