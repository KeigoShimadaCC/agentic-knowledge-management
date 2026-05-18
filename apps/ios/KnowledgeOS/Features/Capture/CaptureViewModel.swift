import Foundation
import Observation

@MainActor
@Observable
final class CaptureViewModel {
    struct CreatedNote: Identifiable, Equatable {
        let id: UUID
        let title: String
        let webURL: URL?
    }

    struct UploadItem: Identifiable, Equatable {
        enum State: Equatable {
            case queued
            case uploading
            case uploaded(sourceID: UUID)
            case ready(sourceID: UUID)
            case failed(String)
            /// Network/5xx failure — handed off to the persistent QueueStore for retry.
            case pending
        }

        let id = UUID()
        let filename: String
        let mimeType: String
        let data: Data
        var progress: Double = 0
        var state: State = .queued
    }

    private let api: any CaptureAPIProtocol
    private let serverConfig: ServerConfig
    private let queueStore: (any QueueStore)?
    private(set) var isSavingNote = false
    private(set) var createdNote: CreatedNote?
    private(set) var noteError: String?
    private(set) var uploads: [UploadItem] = []
    var activeSourceID: UUID?

    init(
        api: any CaptureAPIProtocol,
        serverConfig: ServerConfig = .shared,
        queueStore: (any QueueStore)? = nil
    ) {
        self.api = api
        self.serverConfig = serverConfig
        self.queueStore = queueStore
    }

    func saveQuickNote(title: String, body: String) async {
        let trimmedBody = body.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedBody.isEmpty else {
            noteError = "Add note text before saving."
            return
        }

        isSavingNote = true
        noteError = nil
        defer { isSavingNote = false }

        do {
            let response = try await api.createQuickNote(title: title, body: trimmedBody)
            createdNote = CreatedNote(
                id: response.object.id,
                title: response.object.title,
                webURL: Self.webPageURL(for: response.object.id, apiBaseURL: serverConfig.baseURL)
            )
        } catch let error as APIError {
            if Self.isRetryable(error), let queueStore {
                let resolvedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                    ? "Quick note" : title
                let request = PageCreateRequest(
                    title: resolvedTitle,
                    contentJson: KnowledgeOSCaptureAPI.tiptapDocument(from: trimmedBody)
                )
                if let payload = try? JSONCoding.encoder.encode(request) {
                    let now = Date()
                    let item = PendingUpload(
                        id: UUID(),
                        kind: .quickNote,
                        payload: payload,
                        metadata: Data(),
                        retryCount: 0,
                        lastError: error.userMessage,
                        createdAt: now,
                        nextAttemptAt: now
                    )
                    try? queueStore.enqueue(item)
                    noteError = "Saved offline. Will sync when the server is reachable."
                    return
                }
            }
            noteError = error.userMessage
        } catch {
            noteError = error.localizedDescription
        }
    }

    func enqueueUpload(data: Data, filename: String, mimeType: String) {
        uploads.insert(UploadItem(filename: filename, mimeType: mimeType, data: data), at: 0)
    }

    func uploadQueuedItems() async {
        let queued = uploads.filter {
            if case .queued = $0.state { return true }
            return false
        }

        for item in queued {
            await upload(itemID: item.id)
        }
    }

    func retry(itemID: UUID) async {
        guard let index = uploads.firstIndex(where: { $0.id == itemID }) else { return }
        uploads[index].state = .queued
        uploads[index].progress = 0
        await upload(itemID: itemID)
    }

    func refresh(sourceID: UUID) async -> SourceDTO? {
        do {
            let source = try await api.source(id: sourceID)
            if source.ingestionStatus == "ready" {
                markSource(sourceID, as: .ready(sourceID: sourceID), progress: 1)
            } else if source.ingestionStatus == "failed" {
                markSource(sourceID, as: .failed(source.errorMessage ?? "Ingestion failed."), progress: 1)
            }
            return source
        } catch {
            return nil
        }
    }

    private func upload(itemID: UUID) async {
        guard let index = uploads.firstIndex(where: { $0.id == itemID }) else { return }
        uploads[index].state = .uploading
        uploads[index].progress = 0.15

        do {
            let response = try await api.upload(
                data: uploads[index].data,
                filename: uploads[index].filename,
                mimeType: uploads[index].mimeType
            )
            uploads[index].state = .uploaded(sourceID: response.source.id)
            uploads[index].progress = 1
            activeSourceID = response.source.id
        } catch let error as APIError {
            handleUploadFailure(index: index, error: error.userMessage, retryable: Self.isRetryable(error))
        } catch {
            handleUploadFailure(index: index, error: error.localizedDescription, retryable: true)
        }
    }

    private func handleUploadFailure(index: Int, error: String, retryable: Bool) {
        let item = uploads[index]
        if retryable, let queueStore {
            let now = Date()
            let pending = PendingUpload(
                id: UUID(),
                kind: .assetUpload(filename: item.filename, mimeType: item.mimeType, createSource: true),
                payload: item.data,
                metadata: (try? PendingUploadKind.assetUpload(
                    filename: item.filename, mimeType: item.mimeType, createSource: true
                ).encodedMetadata()) ?? Data(),
                retryCount: 0,
                lastError: error,
                createdAt: now,
                nextAttemptAt: now
            )
            try? queueStore.enqueue(pending)
            uploads[index].state = .pending
            uploads[index].progress = 1
        } else {
            uploads[index].state = .failed(error)
            uploads[index].progress = 1
        }
    }

    private func markSource(_ sourceID: UUID, as state: UploadItem.State, progress: Double) {
        guard let index = uploads.firstIndex(where: { item in
            switch item.state {
            case let .uploaded(id), let .ready(id):
                return id == sourceID
            default:
                return false
            }
        }) else {
            return
        }
        uploads[index].state = state
        uploads[index].progress = progress
    }

    static func webPageURL(for pageID: UUID, apiBaseURL: URL) -> URL? {
        guard var components = URLComponents(url: apiBaseURL, resolvingAgainstBaseURL: false) else {
            return nil
        }
        components.port = 3000
        components.path = "/app/pages/\(pageID.uuidString)"
        components.query = nil
        components.fragment = nil
        return components.url
    }

    /// Network errors and 5xx are retryable. Validation (4xx) is not — no point queuing.
    static func isRetryable(_ error: APIError) -> Bool {
        switch error {
        case .networkUnavailable, .serverError:
            return true
        case .notAuthenticated, .forbidden, .notFound, .validation, .aiDisabled, .decodingFailed:
            return false
        }
    }
}
