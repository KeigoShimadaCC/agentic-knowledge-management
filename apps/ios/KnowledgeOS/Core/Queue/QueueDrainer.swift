import Foundation

struct DrainSummary: Equatable {
    var attempted: Int = 0
    var succeeded: Int = 0
    var failed: Int = 0
}

/// Drains pending uploads from a QueueStore using a real APIClient. Used by:
///  - foreground reachability-change handler in CaptureViewModel
///  - BGAppRefreshTask handler (quick budget)
///  - BGProcessingTask handler (longer budget)
struct QueueDrainer: Sendable {
    private let queue: any QueueStore
    private let apiClient: any APIClientProtocol
    private let keychain: any KeychainStore

    init(
        queue: any QueueStore,
        apiClient: any APIClientProtocol = APIClient(),
        keychain: any KeychainStore = SystemKeychainStore()
    ) {
        self.queue = queue
        self.apiClient = apiClient
        self.keychain = keychain
    }

    /// Drains drainable items, executing each via APIClient. `deadline` lets BG handlers
    /// bound the work (e.g. `Date() + 25` for BGAppRefreshTask).
    @discardableResult
    func drain(now: Date = Date(), deadline: Date? = nil) async -> DrainSummary {
        // Make sure the API client has a token (we may be running in a background task
        // where AuthStore.restoreSessionIfNeeded() hasn't run yet).
        if apiClient.bearerToken == nil,
           let token = try? keychain.readToken() {
            apiClient.setBearerToken(token)
        }

        var summary = DrainSummary()
        guard let items = try? queue.nextDrainable(now: now) else { return summary }

        for item in items {
            if let deadline, Date() >= deadline { break }
            summary.attempted += 1
            do {
                try await execute(item)
                try? queue.markSucceeded(id: item.id)
                summary.succeeded += 1
            } catch {
                let message = (error as? APIError)?.userMessage ?? error.localizedDescription
                try? queue.markFailed(id: item.id, error: message, now: now)
                summary.failed += 1
            }
        }
        return summary
    }

    private func execute(_ item: PendingUpload) async throws {
        switch item.kind {
        case .quickNote:
            // payload is JSON-encoded PageCreateRequest
            let request = try JSONCoding.decoder.decode(PageCreateRequest.self, from: item.payload)
            let _: PageCreateResponseDTO = try await apiClient.request(
                .createPage,
                body: request,
                auth: true
            )

        case let .assetUpload(filename, mimeType, createSource):
            let upload = MultipartUpload(filename: filename, mimeType: mimeType, fileData: item.payload)
            _ = try await apiClient.uploadMultipart(
                .assetUpload(createSource: createSource),
                upload: upload,
                auth: true
            )
        }
    }
}
