import Foundation

@MainActor
final class ConnectViewModel: ObservableObject {
    enum ResultState: Equatable {
        case idle
        case loading
        case success(String)
        case failure(String)
    }

    @Published private(set) var resultState: ResultState = .idle

    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func testConnection(baseURLText: String) async -> URL? {
        guard let baseURL = makeBaseURL(from: baseURLText) else {
            resultState = .failure("Enter a valid HTTP or HTTPS server URL.")
            return nil
        }

        resultState = .loading

        do {
            let healthURL = baseURL.appending(path: "api/v1/health")
            var request = URLRequest(url: healthURL)
            request.httpMethod = "GET"
            request.timeoutInterval = 10

            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                resultState = .failure("The server returned an invalid response.")
                return nil
            }

            guard (200..<300).contains(httpResponse.statusCode) else {
                resultState = .failure("Health check failed with HTTP \(httpResponse.statusCode).")
                return nil
            }

            let health = try JSONCoding.decoder.decode(HealthResponse.self, from: data)
            guard health.status == "ok" else {
                resultState = .failure("Health check returned unexpected status.")
                return nil
            }

            resultState = .success("Connection passed.")
            return baseURL
        } catch {
            resultState = .failure(error.localizedDescription)
            return nil
        }
    }

    private func makeBaseURL(from text: String) -> URL? {
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
