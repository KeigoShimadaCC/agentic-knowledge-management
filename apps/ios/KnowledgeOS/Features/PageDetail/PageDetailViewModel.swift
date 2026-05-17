import Foundation
import Observation

@MainActor
@Observable
final class PageDetailViewModel {
    private let api: ReadAPI
    private let editAPI: EditAPI
    private(set) var page: PageDTO?
    private(set) var isLoading = false
    private(set) var errorMessage: String?
    var conflict: PageConflict?

    init(api: ReadAPI = ReadAPI(), editAPI: EditAPI = EditAPI()) {
        self.api = api
        self.editAPI = editAPI
    }

    func load(id: UUID) async {
        guard page?.id != id else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            page = try await api.page(id: id)
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }

    func apply(updated: PageDTO) {
        page = updated
    }

    /// Discard local draft: re-fetch the server's current page so the editor reopens with fresh state.
    func discardAndRefresh(pageID: UUID) async {
        do {
            page = try await editAPI.page(id: pageID)
        } catch {
            errorMessage = readErrorMessage(error)
        }
        conflict = nil
    }

    /// Force-save the conflicting draft after fetching the current server version.
    func overwriteWith(draftText: String, pageID: UUID) async {
        do {
            let fresh = try await editAPI.page(id: pageID)
            let doc = TiptapPlainText.tiptapDocument(from: draftText)
            let text = TiptapPlainText.extractPlainText(from: doc)
            let saved = try await editAPI.updatePage(
                id: pageID,
                title: nil,
                contentJson: doc,
                contentText: text,
                expectedVersion: fresh.version
            )
            page = saved
        } catch {
            errorMessage = readErrorMessage(error)
        }
        conflict = nil
    }
}
