import SwiftUI

struct HomeTab: View {
    @Environment(AuthStore.self) private var authStore

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                ObjectKindBadge(kind: "home")

                Text("Welcome")
                    .font(.title.weight(.semibold))

                if let user = authStore.currentUser {
                    Text(user.displayName.isEmpty ? user.email : user.displayName)
                        .font(.title2)
                        .accessibilityIdentifier("home.username")
                }

                Text("Home features arrive in PHONE-03A.")
                    .foregroundStyle(.secondary)

                if ProcessInfo.processInfo.arguments.contains("-ui-testing-reset") {
                    Button("Sign Out") {
                        Task { await authStore.logout() }
                    }
                    .accessibilityIdentifier("ui-test.signout")
                }

                Spacer()
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
            .navigationTitle("Home")
        }
        .accessibilityIdentifier("home.tab")
    }
}
