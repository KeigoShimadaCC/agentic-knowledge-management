import SwiftUI

struct EditBodySheet: View {
    let page: PageDTO
    let objectTitle: String
    let onSaved: (PageDTO) -> Void
    let onConflict: (PageConflict) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: String
    @State private var isSaving = false
    @State private var errorMessage: String?

    private let api: EditAPI

    init(
        page: PageDTO,
        objectTitle: String,
        api: EditAPI = EditAPI(),
        onSaved: @escaping (PageDTO) -> Void,
        onConflict: @escaping (PageConflict) -> Void
    ) {
        self.page = page
        self.objectTitle = objectTitle
        self.api = api
        self.onSaved = onSaved
        self.onConflict = onConflict
        let initial = page.contentText.isEmpty
            ? TiptapPlainText.extractPlainText(from: page.contentJson)
            : page.contentText
        _draft = State(initialValue: initial)
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                TextEditor(text: $draft)
                    .font(.body)
                    .padding(.horizontal, 12)
                    .padding(.top, 8)
                    .accessibilityIdentifier(Kos.EditBody.editor)

                if let errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .accessibilityIdentifier(Kos.EditBody.errorBanner)
                }
            }
            .navigationTitle("Edit body")
            .navigationBarTitleDisplayMode(.inline)
            .accessibilityIdentifier(Kos.EditBody.screen)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .accessibilityIdentifier(Kos.EditBody.cancelButton)
                        .disabled(isSaving)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task { await save() }
                    }
                    .disabled(isSaving || !isDirty)
                    .accessibilityIdentifier(Kos.EditBody.saveButton)
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

    private var isDirty: Bool {
        let currentPlain = page.contentText.isEmpty
            ? TiptapPlainText.extractPlainText(from: page.contentJson)
            : page.contentText
        return draft != currentPlain
    }

    private func save() async {
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        let doc = TiptapPlainText.tiptapDocument(from: draft)
        let text = TiptapPlainText.extractPlainText(from: doc)

        do {
            let updated = try await api.updatePage(
                id: page.id,
                title: nil,
                contentJson: doc,
                contentText: text,
                expectedVersion: page.version
            )
            onSaved(updated)
            dismiss()
        } catch let error as APIError {
            if case .conflict = error {
                onConflict(PageConflict(pageID: page.id, draftText: draft))
                dismiss()
            } else {
                errorMessage = error.userMessage
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct PageConflict: Identifiable, Equatable {
    let id = UUID()
    let pageID: UUID
    let draftText: String
}
