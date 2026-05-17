import SwiftUI

struct ConnectView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = ConnectViewModel()

    var body: some View {
        Form {
            Section("Server") {
                TextField("API base URL", text: Binding(
                    get: { appState.baseURLString },
                    set: { appState.updateBaseURL($0) }
                ))
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.URL)
                .accessibilityIdentifier("connect.baseURL")
            }

            Section {
                Button {
                    Task {
                        appState.markChecking()
                        if let baseURL = await viewModel.testConnection(baseURLText: appState.baseURLString) {
                            appState.markConnected(baseURL: baseURL)
                        } else if case let .failure(message) = viewModel.resultState {
                            appState.markFailed(message)
                        }
                    }
                } label: {
                    HStack {
                        Text("Test Connection")
                        if case .loading = viewModel.resultState {
                            Spacer()
                            ProgressView()
                        }
                    }
                }
                .disabled(isTesting)
                .accessibilityIdentifier("connect.testConnection")
            }

            Section {
                statusView
            }
        }
        .accessibilityIdentifier("connect.screen")
    }

    private var isTesting: Bool {
        if case .loading = viewModel.resultState {
            return true
        }
        return false
    }

    @ViewBuilder
    private var statusView: some View {
        switch viewModel.resultState {
        case .idle:
            Text("Enter the Mac API URL and test the connection.")
                .foregroundStyle(.secondary)
                .accessibilityIdentifier("connect.status.idle")
        case .loading:
            HStack {
                ProgressView()
                Text("Checking /api/v1/health")
            }
            .accessibilityIdentifier("connect.status.loading")
        case let .success(message):
            Label(message, systemImage: "checkmark.circle.fill")
                .foregroundStyle(.green)
                .accessibilityIdentifier("connect.status.success")
        case let .failure(message):
            Label(message, systemImage: "xmark.octagon.fill")
                .foregroundStyle(.red)
                .accessibilityIdentifier("connect.status.failure")
        }
    }
}

#Preview {
    NavigationStack {
        ConnectView()
            .environmentObject(AppState(serverConfig: ServerConfig(storage: .init(suiteName: "preview-connect")!)))
    }
}
