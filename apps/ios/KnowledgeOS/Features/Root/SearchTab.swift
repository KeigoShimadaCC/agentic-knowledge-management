import SwiftUI

struct SearchTab: View {
    var body: some View {
        NavigationStack {
            EmptyStateView(
                title: "Search",
                message: "Hybrid search UI arrives in PHONE-03A."
            )
            .navigationTitle("Search")
        }
        .accessibilityIdentifier("search.tab")
    }
}
