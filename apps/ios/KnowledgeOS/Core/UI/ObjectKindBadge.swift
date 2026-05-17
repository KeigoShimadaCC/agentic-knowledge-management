import SwiftUI

struct ObjectKindBadge: View {
    let kind: String

    var body: some View {
        Text(kind.uppercased())
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .foregroundStyle(.blue)
            .background(.blue.opacity(0.12), in: Capsule())
            .accessibilityLabel("\(kind) object")
    }
}
