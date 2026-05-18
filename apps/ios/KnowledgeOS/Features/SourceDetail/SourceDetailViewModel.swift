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
    private(set) var downloadFileURL: URL?
    private(set) var isDownloading = false
    private(set) var downloadErrorMessage: String?
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

        downloadFileURL = nil
        downloadErrorMessage = nil

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

    func downloadAssetForSharing() async {
        guard let source, let assetId = source.assetId else { return }
        isDownloading = true
        downloadErrorMessage = nil
        defer { isDownloading = false }

        do {
            let data = try await api.assetDownload(id: assetId)
            let url = try writeTemporaryDownload(data: data, source: source)
            downloadFileURL = url
        } catch {
            downloadErrorMessage = readErrorMessage(error)
        }
    }

    private func writeTemporaryDownload(data: Data, source: SourceDTO) throws -> URL {
        let name = Self.downloadFilename(for: source)
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("knowledgeos-downloads", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent(name)
        try data.write(to: url, options: [.atomic])
        return url
    }

    private static func downloadFilename(for source: SourceDTO) -> String {
        let trimmed = source.title.trimmingCharacters(in: .whitespacesAndNewlines)
        let base = trimmed.isEmpty ? "source-\(source.id.uuidString)" : trimmed
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._- "))
        let sanitized = String(base.unicodeScalars.map { allowed.contains($0) ? Character($0) : "-" })
            .trimmingCharacters(in: CharacterSet(charactersIn: ". "))
        let safeBase = sanitized.isEmpty ? "source-\(source.id.uuidString)" : sanitized
        guard !safeBase.contains(".") else { return safeBase }
        switch source.sourceType {
        case "pdf": return "\(safeBase).pdf"
        case "image": return "\(safeBase).jpg"
        case "csv": return "\(safeBase).csv"
        case "audio": return "\(safeBase).m4a"
        case "video": return "\(safeBase).mp4"
        default: return safeBase
        }
    }
}
