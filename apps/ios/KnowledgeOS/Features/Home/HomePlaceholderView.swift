import SwiftUI

struct HomePlaceholderView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            ObjectKindBadge(kind: "home")

            Text("Connected")
                .font(.title.weight(.semibold))

            Text("API client coming in PHONE-02A.")
                .foregroundStyle(.secondary)

            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .accessibilityIdentifier(Kos.Home.placeholder)
    }
}

#Preview {
    HomePlaceholderView()
}
