import SwiftUI

struct EditMetadataSheet: View {
    let object: ObjectDTO
    let onSaved: (ObjectDTO) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var title: String
    @State private var tags: [String]
    @State private var isSaving = false
    @State private var errorMessage: String?

    private let api: EditAPI

    init(object: ObjectDTO, api: EditAPI = EditAPI(), onSaved: @escaping (ObjectDTO) -> Void) {
        self.object = object
        self.api = api
        self.onSaved = onSaved
        _title = State(initialValue: object.title)
        _tags = State(initialValue: object.tags)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Title") {
                    TextField("Title", text: $title)
                        .textInputAutocapitalization(.sentences)
                        .submitLabel(.done)
                        .accessibilityIdentifier(Kos.EditMetadata.titleField)
                }

                Section("Tags") {
                    TagChipEditor(tags: $tags)
                }

                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                            .accessibilityIdentifier(Kos.EditMetadata.errorBanner)
                    }
                }
            }
            .navigationTitle("Edit")
            .navigationBarTitleDisplayMode(.inline)
            .accessibilityIdentifier(Kos.EditMetadata.screen)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .accessibilityIdentifier(Kos.EditMetadata.cancelButton)
                        .disabled(isSaving)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(isSaving || trimmedTitle.isEmpty || !isDirty)
                    .accessibilityIdentifier(Kos.EditMetadata.saveButton)
                }
            }
            .overlay {
                if isSaving {
                    Color.black.opacity(0.05).ignoresSafeArea()
                    ProgressView()
                }
            }
        }
        .interactiveDismissDisabled(isSaving)
    }

    private var trimmedTitle: String {
        title.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var isDirty: Bool {
        trimmedTitle != object.title || tags != object.tags
    }

    private func save() async {
        let newTitle = trimmedTitle
        guard !newTitle.isEmpty else { return }
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        let payloadTitle: String? = newTitle == object.title ? nil : newTitle
        let payloadTags: [String]? = tags == object.tags ? nil : tags

        do {
            let updated = try await api.updateObject(
                id: object.id,
                title: payloadTitle,
                description: nil,
                tags: payloadTags
            )
            onSaved(updated)
            dismiss()
        } catch {
            errorMessage = readErrorMessage(error)
        }
    }
}
