import Foundation
import Observation

@MainActor
@Observable
final class GraphLinksViewModel {
    private let graphAPI: GraphAPI
    private let readAPI: ReadAPI
    private(set) var outgoing: [EdgeDTO] = []
    private(set) var backlinks: [EdgeDTO] = []
    private(set) var searchResults: [HybridSearchResultDTO] = []
    private(set) var isLoading = false
    private(set) var isSearching = false
    private(set) var isMutating = false
    private(set) var errorMessage: String?

    init(graphAPI: GraphAPI = GraphAPI(), readAPI: ReadAPI = ReadAPI()) {
        self.graphAPI = graphAPI
        self.readAPI = readAPI
    }

    func load(objectID: UUID) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            async let outgoingEdges = graphAPI.outgoingEdges(objectID: objectID)
            async let incomingEdges = graphAPI.backlinks(objectID: objectID)
            outgoing = try await outgoingEdges
            backlinks = try await incomingEdges
        } catch {
            errorMessage = graphErrorMessage(error)
        }
    }

    func searchTargets(query: String, excluding objectID: UUID) async {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else {
            searchResults = []
            return
        }

        isSearching = true
        defer { isSearching = false }

        do {
            let response = try await readAPI.search(query: trimmed, limit: 8)
            searchResults = response.results.filter { $0.id != objectID }
        } catch {
            errorMessage = graphErrorMessage(error)
        }
    }

    func createLink(sourceID: UUID, targetID: UUID, kind: String) async {
        isMutating = true
        errorMessage = nil
        defer { isMutating = false }

        do {
            _ = try await graphAPI.createEdge(sourceID: sourceID, targetID: targetID, kind: kind)
            await load(objectID: sourceID)
        } catch {
            errorMessage = graphErrorMessage(error)
        }
    }

    func delete(_ edge: EdgeDTO, objectID: UUID) async {
        isMutating = true
        errorMessage = nil
        defer { isMutating = false }

        do {
            _ = try await graphAPI.deleteEdge(id: edge.id)
            await load(objectID: objectID)
        } catch {
            errorMessage = graphErrorMessage(error)
        }
    }
}

func graphErrorMessage(_ error: Error) -> String {
    if let apiError = error as? APIError {
        return apiError.userMessage
    }
    return error.localizedDescription
}
