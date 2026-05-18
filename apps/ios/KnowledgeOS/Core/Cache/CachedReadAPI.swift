import Foundation

/// Stale-while-revalidate wrapper over `ReadAPI`. Each method returns an `AsyncStream`
/// that yields the cached value first (if any) and then the fresh value (or a failure
/// if no cache and the API errored).
///
/// ViewModels consume these with `for await result in api.recentObjects(page: 1) { ... }`.
struct CachedReadAPI: Sendable {
    private let read: ReadAPI
    private let cache: any CacheStore
    private let listTTL: TimeInterval
    private let detailTTL: TimeInterval

    init(
        read: ReadAPI = ReadAPI(),
        cache: any CacheStore,
        listTTL: TimeInterval = 5 * 60,
        detailTTL: TimeInterval = 60 * 60
    ) {
        self.read = read
        self.cache = cache
        self.listTTL = listTTL
        self.detailTTL = detailTTL
    }

    typealias Output<T> = Result<T, APIError>

    // MARK: - Lists

    func recentObjects(page: Int, limit: Int = 25) -> AsyncStream<Output<PaginatedResponseDTO<ObjectDTO>>> {
        stream(
            cached: cache.cachedRecentObjects(page: page),
            fetch: { try await read.recentObjects(page: page, limit: limit) },
            save: { try? cache.saveRecentObjects(page: page, response: $0) }
        )
    }

    func search(query: String, limit: Int = 25) -> AsyncStream<Output<HybridSearchResponseDTO>> {
        stream(
            cached: cache.cachedSearch(query: query),
            fetch: { try await read.search(query: query, limit: limit) },
            save: { try? cache.saveSearch(query: query, response: $0) }
        )
    }

    // MARK: - Details

    func object(id: UUID) -> AsyncStream<Output<ObjectDTO>> {
        stream(
            cached: cache.cachedObject(id: id),
            fetch: { try await read.object(id: id) },
            save: { try? cache.saveObject($0) }
        )
    }

    func page(id: UUID) -> AsyncStream<Output<PageDTO>> {
        stream(
            cached: cache.cachedPage(id: id),
            fetch: { try await read.page(id: id) },
            save: { try? cache.savePage(id: id, page: $0) }
        )
    }

    func source(id: UUID) -> AsyncStream<Output<SourceDTO>> {
        stream(
            cached: cache.cachedSource(id: id),
            fetch: { try await read.source(id: id) },
            save: { try? cache.saveSource(id: id, source: $0) }
        )
    }

    func chat(id: UUID) -> AsyncStream<Output<ChatDTO>> {
        stream(
            cached: cache.cachedChat(id: id),
            fetch: { try await read.chat(id: id) },
            save: { try? cache.saveChat(id: id, chat: $0) }
        )
    }

    func project(id: UUID) -> AsyncStream<Output<ProjectDTO>> {
        stream(
            cached: cache.cachedProject(id: id),
            fetch: { try await read.project(id: id) },
            save: { try? cache.saveProject(id: id, project: $0) }
        )
    }

    // MARK: - Pass-through to ReadAPI for surfaces we don't cache yet

    /// Source text and thumbnails are passed through without caching in MVP.
    func sourceText(id: UUID) async throws -> String { try await read.sourceText(id: id) }
    func sourceThumbnail(id: UUID) async throws -> Data { try await read.sourceThumbnail(id: id) }
    func assetDownload(id: UUID) async throws -> Data { try await read.assetDownload(id: id) }
    func relatedObjects(id: UUID) async throws -> [RelatedObjectDTO] {
        try await read.relatedObjects(id: id)
    }

    // MARK: - Internal

    private func stream<T>(
        cached: CachedEntry<T>?,
        fetch: @escaping @Sendable () async throws -> T,
        save: @escaping @Sendable (T) -> Void
    ) -> AsyncStream<Output<T>> {
        AsyncStream { continuation in
            if let cached {
                continuation.yield(.success(cached.value))
            }
            Task {
                do {
                    let fresh = try await fetch()
                    save(fresh)
                    continuation.yield(.success(fresh))
                    continuation.finish()
                } catch let error as APIError {
                    if cached != nil {
                        // Already yielded cached value; swallow the network error so callers
                        // can keep rendering the cached state.
                        continuation.finish()
                    } else {
                        continuation.yield(.failure(error))
                        continuation.finish()
                    }
                } catch {
                    let apiError = APIError.decodingFailed(error.localizedDescription)
                    if cached != nil {
                        continuation.finish()
                    } else {
                        continuation.yield(.failure(apiError))
                        continuation.finish()
                    }
                }
            }
        }
    }
}
