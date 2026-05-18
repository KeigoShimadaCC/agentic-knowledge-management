import Foundation
import Observation
import UIKit

@MainActor
@Observable
final class SourceDetailViewModel {
    private let api: CachedReadAPI
    private(set) var source: SourceDTO?
    private(set) var text = ""
    private(set) var thumbnail: UIImage?
    private(set) var downloadURL: URL?
    private(set) var isLoading = false
    private(set) var errorMessage: String?

    init(api: CachedReadAPI? = nil) {
        if let api {
            self.api = api
        } else {
            self.api = CachedReadAPI(cache: (try? SystemCacheStore()) ?? InMemoryCacheStore())
        }
    }

    func load(id: UUID) async {
        guard source?.id != id else { return }
        isLoading = true
        errorMessage = nil
        var sawAnything = false
        defer { isLoading = false }

        downloadURL = api.sourceDownloadURL(id: id)

        for await result in api.source(id: id) {
            switch result {
            case let .success(value):
                source = value
                errorMessage = nil
                sawAnything = true
                // Source text + thumbnail are pass-through; reload each time we get
                // a fresh source DTO (so the side data follows the fresh state).
                text = (try? await api.sourceText(id: id)) ?? value.extractedText ?? ""
                if let data = try? await api.sourceThumbnail(id: id) {
                    thumbnail = UIImage(data: data)
                }
            case let .failure(error):
                if !sawAnything { errorMessage = error.userMessage }
            }
        }
    }
}
