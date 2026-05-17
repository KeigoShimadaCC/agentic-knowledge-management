import Foundation
#if canImport(UIKit)
import UIKit
#endif

@MainActor
final class LoginViewModel: ObservableObject {
    @Published var email = ""
    @Published var password = ""
    @Published var deviceName = ""
    @Published private(set) var isSubmitting = false
    @Published private(set) var errorMessage: String?

    private let authStore: AuthStore

    init(authStore: AuthStore) {
        self.authStore = authStore
        #if canImport(UIKit)
        deviceName = UIDevice.current.name
        #endif
    }

    var canSubmit: Bool {
        !email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && password.count >= 8
            && !isSubmitting
    }

    func login() async {
        guard canSubmit else {
            errorMessage = "Enter a valid email and password (8+ characters)."
            return
        }

        isSubmitting = true
        errorMessage = nil
        defer { isSubmitting = false }

        let name = deviceName.trimmingCharacters(in: .whitespacesAndNewlines)
        await authStore.login(
            email: email,
            password: password,
            deviceName: name.isEmpty ? nil : name
        )

        if let error = authStore.lastError {
            errorMessage = error
        }
    }
}
