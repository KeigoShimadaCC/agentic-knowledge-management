import SwiftUI

struct ConflictResolutionSheet: View {
    let conflict: PageConflict
    let onDiscard: () async -> Void
    let onKeepMine: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var isWorking = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text("Page changed elsewhere")
                    .font(.title3.weight(.semibold))

                Text("Someone (or another device) saved this page after you opened it. Your draft was not saved.")
                    .foregroundStyle(.secondary)

                if !conflict.draftText.isEmpty {
                    Text("Your draft (first 200 chars):")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.top, 4)
                    Text(String(conflict.draftText.prefix(200)))
                        .font(.footnote)
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 6))
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                Spacer()

                VStack(spacing: 10) {
                    Button {
                        Task { await tap(onKeepMine) }
                    } label: {
                        Text("Keep my changes (overwrite)")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(isWorking)
                    .accessibilityIdentifier(Kos.Conflict.keepMineButton)

                    Button(role: .destructive) {
                        Task { await tap(onDiscard) }
                    } label: {
                        Text("Discard my changes")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .disabled(isWorking)
                    .accessibilityIdentifier(Kos.Conflict.discardButton)
                }
            }
            .padding()
            .navigationTitle("Conflict")
            .navigationBarTitleDisplayMode(.inline)
            .accessibilityIdentifier(Kos.Conflict.screen)
            .overlay {
                if isWorking { ProgressView() }
            }
        }
        .interactiveDismissDisabled(isWorking)
    }

    private func tap(_ action: @escaping () async -> Void) async {
        isWorking = true
        errorMessage = nil
        defer { isWorking = false }
        await action()
        dismiss()
    }
}
