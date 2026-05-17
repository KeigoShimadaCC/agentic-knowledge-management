import Foundation

enum EnvironmentConfig {
    static var defaultBaseURL: URL {
        #if targetEnvironment(simulator)
        URL(string: "http://127.0.0.1:8001")!
        #else
        URL(string: "http://127.0.0.1:8001")!
        #endif
    }

    static var isDebugBuild: Bool {
        #if DEBUG
        true
        #else
        false
        #endif
    }

    static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        true
        #else
        false
        #endif
    }
}
