import SwiftUI

struct LoginView: View {
    @Environment(AuthStore.self) private var authStore

    var body: some View {
        LoginForm(authStore: authStore)
    }
}

private struct LoginForm: View {
    @Environment(AuthStore.self) private var authStore
    @StateObject private var viewModel: LoginViewModel
    @FocusState private var focusedField: Field?

    private enum Field {
        case email
        case password
        case deviceName
    }

    init(authStore: AuthStore) {
        _viewModel = StateObject(wrappedValue: LoginViewModel(authStore: authStore))
    }

    var body: some View {
        Form {
            Section("Account") {
                TextField("Email", text: $viewModel.email)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.emailAddress)
                    .focused($focusedField, equals: .email)
                    .accessibilityIdentifier("login.email")

                SecureField("Password", text: $viewModel.password)
                    .focused($focusedField, equals: .password)
                    .accessibilityIdentifier("login.password")
            }

            Section("Device") {
                TextField("Device name", text: $viewModel.deviceName)
                    .focused($focusedField, equals: .deviceName)
                    .accessibilityIdentifier("login.deviceName")
            }

            if let error = viewModel.errorMessage {
                Section {
                    Text(error)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("login.error")
                }
            }

            Section {
                Button {
                    focusedField = nil
                    Task { await viewModel.login() }
                } label: {
                    HStack {
                        Text("Sign In")
                        if viewModel.isSubmitting || authStore.isLoading {
                            Spacer()
                            ProgressView()
                        }
                    }
                }
                .disabled(!viewModel.canSubmit)
                .accessibilityIdentifier("login.submit")
            }
        }
        .accessibilityIdentifier("login.screen")
    }
}
