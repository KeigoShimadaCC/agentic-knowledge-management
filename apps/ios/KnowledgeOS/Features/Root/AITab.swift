import SwiftUI

struct AITab: View {
    var body: some View {
        NavigationStack {
            AskKBView()
                .navigationDestination(for: ObjectRoute.self) { route in
                    ObjectDetailView(route: route)
                }
        }
        .accessibilityIdentifier("ai.tab")
    }
}
