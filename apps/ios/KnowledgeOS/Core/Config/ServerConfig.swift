import Foundation

final class ServerConfig {
    static let shared = ServerConfig()

    private enum Key {
        static let baseURL = "knowledgeos.baseURL"
    }

    private let storage: UserDefaults

    init(storage: UserDefaults = .standard) {
        self.storage = storage
    }

    var baseURL: URL {
        if let value = storage.string(forKey: Key.baseURL),
           let url = URL(string: value),
           url.scheme != nil,
           url.host != nil {
            return url.normalizedBaseURL
        }

        return EnvironmentConfig.defaultBaseURL
    }

    func saveBaseURL(_ url: URL) {
        storage.set(url.normalizedBaseURL.absoluteString, forKey: Key.baseURL)
    }

    func reset() {
        storage.removeObject(forKey: Key.baseURL)
    }
}

extension URL {
    var normalizedBaseURL: URL {
        var text = absoluteString
        while text.count > 1, text.hasSuffix("/") {
            text.removeLast()
        }
        return URL(string: text) ?? self
    }
}
