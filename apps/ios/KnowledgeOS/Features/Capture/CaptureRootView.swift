import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

struct CaptureRootView: View {
    @Bindable var viewModel: CaptureViewModel
    @State private var title = ""
    @State private var bodyText = ""
    @State private var selectedPhotos: [PhotosPickerItem] = []
    @State private var showFileImporter = false
    @State private var showSuccessToast = false

    var body: some View {
        List {
            Section("Quick Note") {
                TextField("Title", text: $title)
                    .accessibilityIdentifier(Kos.Capture.titleField)

                TextEditor(text: $bodyText)
                    .frame(minHeight: 140)
                    .accessibilityIdentifier(Kos.Capture.noteField)

                HStack {
                    Button {
                        pasteClipboard()
                    } label: {
                        Label("Paste", systemImage: "doc.on.clipboard")
                    }
                    .accessibilityIdentifier(Kos.Capture.pasteButton)

                    Spacer()

                    Button {
                        Task { await saveQuickNote() }
                    } label: {
                        if viewModel.isSavingNote {
                            ProgressView()
                        } else {
                            Label("Save", systemImage: "square.and.arrow.down")
                        }
                    }
                    .disabled(viewModel.isSavingNote)
                    .accessibilityIdentifier(Kos.Capture.saveButton)
                }

                if let noteError = viewModel.noteError {
                    Text(noteError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                if let createdNote = viewModel.createdNote {
                    NavigationLink {
                        CreatedPageView(note: createdNote)
                    } label: {
                        Label(createdNote.title, systemImage: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                    }
                    .accessibilityIdentifier(Kos.Capture.successLink)
                }
            }

            Section("Upload") {
                PhotosPicker(selection: $selectedPhotos, maxSelectionCount: 10, matching: .images) {
                    Label("Choose Photos", systemImage: "photo.on.rectangle")
                }
                .accessibilityIdentifier(Kos.Upload.photoButton)

                Button {
                    showFileImporter = true
                } label: {
                    Label("Choose Files", systemImage: "folder")
                }
                .accessibilityIdentifier(Kos.Upload.pickButton)

                ForEach(viewModel.uploads) { item in
                    UploadRow(item: item) {
                        Task { await viewModel.retry(itemID: item.id) }
                    }
                }
            }
        }
        .navigationTitle("Capture")
        .accessibilityIdentifier(Kos.Capture.screen)
        .overlay(alignment: .bottom) {
            if showSuccessToast, let createdNote = viewModel.createdNote {
                Label("Saved \(createdNote.title)", systemImage: "checkmark.circle.fill")
                    .font(.subheadline.weight(.semibold))
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(.regularMaterial, in: Capsule())
                    .padding(.bottom, 20)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .fileImporter(
            isPresented: $showFileImporter,
            allowedContentTypes: [.image, .pdf, .plainText, .commaSeparatedText, .data, .item],
            allowsMultipleSelection: true
        ) { result in
            handleFileImport(result)
        }
        .onChange(of: selectedPhotos) { _, newItems in
            Task { await handlePhotos(newItems) }
        }
        .navigationDestination(item: $viewModel.activeSourceID) { sourceID in
            SourceStatusView(sourceID: sourceID, viewModel: viewModel)
        }
    }

    private func pasteClipboard() {
        guard let clipboard = UIPasteboard.general.string, !clipboard.isEmpty else { return }
        bodyText = bodyText.isEmpty ? clipboard : "\(bodyText)\n\(clipboard)"
    }

    private func saveQuickNote() async {
        await viewModel.saveQuickNote(title: title, body: bodyText)
        guard viewModel.createdNote != nil else { return }
        bodyText = ""
        title = ""
        withAnimation {
            showSuccessToast = true
        }
        try? await Task.sleep(nanoseconds: 2_000_000_000)
        withAnimation {
            showSuccessToast = false
        }
    }

    private func handlePhotos(_ items: [PhotosPickerItem]) async {
        selectedPhotos = []
        for item in items {
            guard let data = try? await item.loadTransferable(type: Data.self) else { continue }
            let filename = "\(UUID().uuidString).jpg"
            viewModel.enqueueUpload(data: data, filename: filename, mimeType: "image/jpeg")
        }
        await viewModel.uploadQueuedItems()
    }

    private func handleFileImport(_ result: Result<[URL], Error>) {
        guard case let .success(urls) = result else { return }
        Task {
            for url in urls {
                let didStart = url.startAccessingSecurityScopedResource()
                defer {
                    if didStart {
                        url.stopAccessingSecurityScopedResource()
                    }
                }
                guard let data = try? Data(contentsOf: url) else { continue }
                viewModel.enqueueUpload(
                    data: data,
                    filename: url.lastPathComponent,
                    mimeType: mimeType(for: url)
                )
            }
            await viewModel.uploadQueuedItems()
        }
    }

    private func mimeType(for url: URL) -> String {
        if let type = UTType(filenameExtension: url.pathExtension),
           let mime = type.preferredMIMEType {
            return mime
        }
        return "application/octet-stream"
    }
}

private struct UploadRow: View {
    let item: CaptureViewModel.UploadItem
    let retry: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(item.filename)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                statusLabel
            }

            ProgressView(value: item.progress)

            if case let .failed(message) = item.state {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(.red)
                Button {
                    retry()
                } label: {
                    Label("Retry", systemImage: "arrow.clockwise")
                }
                .accessibilityIdentifier(Kos.Upload.retryButton)
            }
        }
        .accessibilityIdentifier(Kos.Upload.statusLabel)
    }

    @ViewBuilder
    private var statusLabel: some View {
        switch item.state {
        case .queued:
            Text("Queued")
        case .uploading:
            Text("Uploading")
        case .uploaded:
            Text("Ingesting")
        case .ready:
            Text("Ready")
                .foregroundStyle(.green)
        case .failed:
            Text("Failed")
                .foregroundStyle(.red)
        case .pending:
            Text("Will retry automatically")
                .foregroundStyle(.orange)
        }
    }
}

private struct CreatedPageView: View {
    let note: CaptureViewModel.CreatedNote

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Page created", systemImage: "checkmark.circle.fill")
                .font(.title2.weight(.semibold))
                .foregroundStyle(.green)
            Text(note.title)
                .font(.headline)
            Text(note.id.uuidString)
                .font(.footnote.monospaced())
                .foregroundStyle(.secondary)
            if let webURL = note.webURL {
                Link(destination: webURL) {
                    Label("Open in KnowledgeOS Web", systemImage: "safari")
                }
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .navigationTitle("New Page")
    }
}
