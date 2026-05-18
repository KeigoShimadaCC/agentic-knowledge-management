import XCTest
@testable import KnowledgeOS

/// Live-backend smoke for PHASE-PHONE-04 edit-lite, exercising the edit flow end-to-end
/// through `EditAPI` against `docker compose up` — without XCUITest. Mirrors the pattern
/// established by `LiveBackendSmokeTests`: iOS 26 simulator XCUITest is flaky for List
/// cells and NavigationLinks; this proves the same code paths via APIClient + EditAPI.
///
/// Verifies:
///   - PATCH /objects/{id} updates title + tags and persists.
///   - PUT /pages/{id} with valid Tiptap doc and `expected_version` succeeds and bumps version.
///   - PUT /pages/{id} with a stale `expected_version` returns 409 → mapped to APIError.conflict.
///
/// Skips automatically when the backend is unreachable.
@MainActor
final class EditLiteLiveSmokeTests: XCTestCase {
    private let baseURL = URL(string: "http://127.0.0.1:8001")!
    private let demoEmail = "demo@example.com"
    private let demoPassword = "demo-demo-demo"

    override func setUp() async throws {
        try await super.setUp()
        guard await backendIsReachable() else {
            throw XCTSkip("Backend not reachable at \(baseURL); skipping edit-lite live smoke.")
        }
    }

    func testEditMetadataAndBodyPersistsWithConflictDetection() async throws {
        let serverConfig = ServerConfig.shared
        serverConfig.saveBaseURL(baseURL)
        let keychain = SmokeKeychain()
        let apiClient = APIClient(serverConfig: serverConfig)

        // Login.
        let login: MobileLoginResponse = try await apiClient.request(
            .mobileLogin,
            body: MobileLoginRequest(email: demoEmail, password: demoPassword, deviceName: "ios-smoke"),
            auth: false
        )
        apiClient.setBearerToken(login.token)
        try keychain.saveToken(login.token)

        let editAPI = EditAPI(apiClient: apiClient, keychain: keychain)
        let readAPI = ReadAPI(apiClient: apiClient, keychain: keychain)

        // Create a fresh page so the test is self-contained and idempotent.
        let originalTitle = "Edit-lite smoke \(Int(Date().timeIntervalSince1970))"
        let created: PageCreateResponseDTO = try await apiClient.request(
            .createPage,
            body: PageCreateRequest(
                title: originalTitle,
                contentJson: TiptapPlainText.tiptapDocument(from: "seed body")
            ),
            auth: true
        )
        let objectID = created.object.id
        let pageID = created.page.id
        XCTAssertEqual(created.object.title, originalTitle)
        XCTAssertEqual(created.object.tags, [])

        // 1) PATCH /objects/{id} title + tags.
        let editedTitle = originalTitle + " · edited"
        let editedTags = ["smoke", "edit-lite"]
        let updatedObject = try await editAPI.updateObject(
            id: objectID,
            title: editedTitle,
            description: nil,
            tags: editedTags
        )
        XCTAssertEqual(updatedObject.title, editedTitle)
        XCTAssertEqual(updatedObject.tags, editedTags)

        // Re-fetch via the read path — proves persistence beyond the immediate response.
        let refetched = try await readAPI.object(id: objectID)
        XCTAssertEqual(refetched.title, editedTitle)
        XCTAssertEqual(refetched.tags, editedTags)

        // 2) PUT /pages/{id} body update with current version succeeds.
        let originalVersion = created.page.version
        let bodyPlain = "First paragraph\n\nSecond paragraph\n\nThird"
        let doc = TiptapPlainText.tiptapDocument(from: bodyPlain)
        let savedPage = try await editAPI.updatePage(
            id: pageID,
            title: nil,
            contentJson: doc,
            contentText: TiptapPlainText.extractPlainText(from: doc),
            expectedVersion: originalVersion
        )
        XCTAssertGreaterThan(savedPage.version, originalVersion, "Saving a body should bump the page version")

        // Round-trip: re-fetch and confirm the body is exactly the three paragraphs we wrote.
        let fetchedPage = try await readAPI.page(id: pageID)
        let fetchedText = TiptapPlainText.extractPlainText(from: fetchedPage.contentJson)
        XCTAssertEqual(fetchedText, "First paragraph\nSecond paragraph\nThird")

        // 3) Stale expected_version should produce 409 → APIError.conflict.
        do {
            _ = try await editAPI.updatePage(
                id: pageID,
                title: nil,
                contentJson: doc,
                contentText: nil,
                expectedVersion: originalVersion // stale on purpose
            )
            XCTFail("Expected APIError.conflict for stale expected_version")
        } catch let error as APIError {
            if case .conflict = error {
                // success
            } else {
                XCTFail("Expected .conflict, got \(error)")
            }
        }
    }

    // MARK: - Helpers

    private func backendIsReachable() async -> Bool {
        if ProcessInfo.processInfo.environment["KOS_LIVE_SMOKE"] == "1" {
            return true
        }
        var request = URLRequest(url: baseURL.appendingPathComponent("/api/v1/health"))
        request.timeoutInterval = 2
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}

private struct SmokeKeychain: KeychainStore {
    private final class Storage: @unchecked Sendable {
        let lock = NSLock()
        var token: String?
    }
    private let storage = Storage()

    func readToken() throws -> String? {
        storage.lock.lock(); defer { storage.lock.unlock() }
        return storage.token
    }

    func saveToken(_ token: String) throws {
        storage.lock.lock(); defer { storage.lock.unlock() }
        storage.token = token
    }

    func deleteToken() throws {
        storage.lock.lock(); defer { storage.lock.unlock() }
        storage.token = nil
    }
}
