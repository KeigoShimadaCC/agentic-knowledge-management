import SwiftUI

struct CaptureTab: View {
    var body: some View {
        NavigationStack {
            EmptyStateView(
                title: "Capture",
                message: "Quick capture arrives in PHONE-03B."
            )
            .navigationTitle("Capture")
        }
        .accessibilityIdentifier("capture.tab")
    }
}
