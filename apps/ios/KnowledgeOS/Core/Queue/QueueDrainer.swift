import Foundation

struct DrainSummary: Equatable {
    var attempted: Int = 0
    var succeeded: Int = 0
    /// Transient failures (network, 5xx) — backoff'd for retry.
    var transientFailed: Int = 0
    /// Permanent failures (4xx — validation, conflict, forbidden, not-found).
    /// These items are parked with `needs_attention = 1` and surface in
    /// `PendingUploadsView`. Spec PHONE-05 task 5.
    var permanentFailed: Int = 0

    var failed: Int { transientFailed + permanentFailed }
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
            } catch let apiError as APIError {
                let message = apiError.userMessage
                if Self.isPermanent(apiError) {
                    try? queue.markNeedsAttention(id: item.id, error: message)
                    summary.permanentFailed += 1
                } else {
                    try? queue.markFailed(id: item.id, error: message, now: now)
                    summary.transientFailed += 1
                }
            } catch {
                try? queue.markFailed(id: item.id, error: error.localizedDescription, now: now)
                summary.transientFailed += 1
            }
        }
        return summary
    }

    /// Permanent (4xx-family) errors — these will not resolve by retrying, so the
    /// item is parked for manual handling. Spec PHONE-05 task 5: "conflicts surface
    /// the same way as PHASE-PHONE-04."
    static func isPermanent(_ error: APIError) -> Bool {
        switch error {
        case .conflict, .validation, .forbidden, .notFound, .notAuthenticated, .aiDisabled:
            return true
        case .networkUnavailable, .serverError, .decodingFailed:
            return false
        }
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
