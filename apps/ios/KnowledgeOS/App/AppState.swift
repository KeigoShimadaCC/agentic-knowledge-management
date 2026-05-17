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

    private let serverConfig: ServerConfig

    init(serverConfig: ServerConfig = .shared) {
        self.serverConfig = serverConfig
        self.baseURLString = serverConfig.baseURL.absoluteString
    }

    var isConnected: Bool {
        connectionState == .connected
    }

    func updateBaseURL(_ text: String) {
        baseURLString = text
        connectionState = .disconnected
    }

    func markChecking() {
        connectionState = .checking
    }

    func markConnected(baseURL: URL) {
        serverConfig.saveBaseURL(baseURL)
        baseURLString = baseURL.absoluteString
        connectionState = .connected
    }

    func markFailed(_ message: String) {
        connectionState = .failed(message)
    }
}
