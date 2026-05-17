import Foundation
import Observation
import UIKit

@MainActor
@Observable
final class SourceDetailViewModel {
    private let api: ReadAPI
    private(set) var source: SourceDTO?
    private(set) var text = ""
    private(set) var thumbnail: UIImage?
    private(set) var downloadURL: URL?
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: ReadAPI = ReadAPI()) {
        self.api = api
    }

    func load(id: UUID) async {
        guard source?.id != id else { return }
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            source = try await api.source(id: id)
            downloadURL = api.sourceDownloadURL(id: id)
            text = (try? await api.sourceText(id: id)) ?? source?.extractedText ?? ""
            if let data = try? await api.sourceThumbnail(id: id) {
                thumbnail = UIImage(data: data)
            }
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
