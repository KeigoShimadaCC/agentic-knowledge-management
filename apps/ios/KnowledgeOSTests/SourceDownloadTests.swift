import XCTest
@testable import KnowledgeOS

@MainActor
final class SourceDownloadTests: XCTestCase {
    func testAssetDownloadUsesAuthenticatedAssetEndpoint() async throws {
        let assetId = UUID(uuidString: "11111111-1111-1111-1111-111111111111")!
        let stub = StubAPIClient(behavior: .succeedWith(Data("asset-bytes".utf8)))
        let api = ReadAPI(apiClient: stub, keychain: InMemoryKeychainStub())

        let data = try await api.assetDownload(id: assetId)

        XCTAssertEqual(data, Data("asset-bytes".utf8))
        let endpoint = try XCTUnwrap(stub.lastDataEndpoint)
        XCTAssertEqual(endpoint.path, "/api/v1/assets/\(assetId.uuidString)/download")
        XCTAssertEqual(stub.lastDataAuth, true)
    }

    func testSourceWithoutAssetHasNoDownloadTarget() throws {
        let source = try FixtureLoader.decode(SourceDTO.self, named: "source")

        XCTAssertNil(source.assetId)
    }
}
