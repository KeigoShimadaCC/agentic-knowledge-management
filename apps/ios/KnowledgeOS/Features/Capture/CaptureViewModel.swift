import Foundation
import Observation

@MainActor
@Observable
final class CaptureViewModel {
    struct CreatedNote: Identifiable, Equatable {
        let id: UUID
        let title: String
    }

    struct UploadItem: Identifiable, Equatable {
        enum State: Equatable {
            case queued
            case uploading
            case uploaded(sourceID: UUID)
            case ready(sourceID: UUID)
            case failed(String)
        }

        let id = UUID()
        let filename: String
        let mimeType: String
        let data: Data
        var progress: Double = 0
        var state: State = .queued
    }

    private let api: any CaptureAPIProtocol
    private(set) var isSavingNote = false
    private(set) var createdNote: CreatedNote?
    private(set) var noteError: String?
    private(set) var uploads: [UploadItem] = []
    var activeSourceID: UUID?

    init(api: any CaptureAPIProtocol) {
        self.api = api
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
            createdNote = CreatedNote(id: response.object.id, title: response.object.title)
        } catch let error as APIError {
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
            uploads[index].state = .failed(error.userMessage)
            uploads[index].progress = 1
        } catch {
            uploads[index].state = .failed(error.localizedDescription)
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
}
