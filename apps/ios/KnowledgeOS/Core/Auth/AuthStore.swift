import Foundation
import Observation

@MainActor
@Observable
final class AuthStore {
    private(set) var currentUser: UserDTO?
    private(set) var capabilities: MobileCapabilitiesDTO?
    private(set) var isAuthenticated = false
    private(set) var isLoading = false
    private(set) var lastError: String?

    private let apiClient: any APIClientProtocol
    private let keychain: KeychainStore
    private var logoutInProgress = false

    init(apiClient: any APIClientProtocol, keychain: KeychainStore = SystemKeychainStore()) {
        self.apiClient = apiClient
        self.keychain = keychain
        apiClient.setUnauthorizedHandler { [weak self] in
            await self?.handleUnauthorized()
        }
    }

    func restoreSessionIfNeeded() async {
        guard !isAuthenticated else { return }
        isLoading = true
        lastError = nil
        defer { isLoading = false }

        do {
            guard let token = try keychain.readToken() else {
                clearLocalState()
                return
            }
            apiClient.setBearerToken(token)
            try await refreshBootstrap()
        } catch {
            clearLocalState()
            try? keychain.deleteToken()
            apiClient.setBearerToken(nil)
        }
    }

    func login(email: String, password: String, deviceName: String?) async {
        isLoading = true
        lastError = nil
        defer { isLoading = false }

        do {
            let request = MobileLoginRequest(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password,
                deviceName: deviceName
            )
            let response: MobileLoginResponse = try await apiClient.request(
                .mobileLogin,
                body: request,
                auth: false
            )
            try keychain.saveToken(response.token)
            apiClient.setBearerToken(response.token)
            currentUser = response.user
            try await refreshBootstrap()
        } catch let error as APIError {
            lastError = error.userMessage
            clearLocalState()
            try? keychain.deleteToken()
            apiClient.setBearerToken(nil)
        } catch {
            lastError = error.localizedDescription
            clearLocalState()
        }
    }

    func logout() async {
        await performLogout(revokeRemote: true)
    }

    func clearSession() {
        Task { await performLogout(revokeRemote: false) }
    }

    func onBaseURLChanged(from oldURL: String?, to newURL: String) {
        guard oldURL != newURL else { return }
        Task { await performLogout(revokeRemote: false) }
    }

    private func refreshBootstrap() async throws {
        let bootstrap: MobileBootstrapResponse = try await apiClient.request(
            .mobileBootstrap,
            body: nil as String?,
            auth: true
        )
        currentUser = bootstrap.user
        capabilities = bootstrap.capabilities
        isAuthenticated = true
    }

    private func handleUnauthorized() async {
        await performLogout(revokeRemote: false)
    }

    private func performLogout(revokeRemote: Bool) async {
        guard !logoutInProgress else { return }
        logoutInProgress = true
        defer { logoutInProgress = false }

        let token = apiClient.bearerToken
        try? keychain.deleteToken()
        apiClient.setBearerToken(nil)
        clearLocalState()

        if revokeRemote, token != nil {
            apiClient.setBearerToken(token)
            let _: OkResponse? = try? await apiClient.request(
                .mobileLogout,
                body: nil as String?,
                auth: true
            )
            apiClient.setBearerToken(nil)
        }
    }

    private func clearLocalState() {
        currentUser = nil
        capabilities = nil
        isAuthenticated = false
    }
}
