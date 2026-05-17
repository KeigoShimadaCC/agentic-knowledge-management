import SwiftUI

struct AskKBView: View {
    @Environment(AuthStore.self) private var authStore
    @State private var viewModel = AskKBViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if viewModel.aiDisabled {
                    AIDisabledBanner()
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Ask KnowledgeOS")
                        .font(.headline)
                    Text("Grounded answers from your KB. Every AI action is user-initiated — nothing runs automatically.")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    TextField("What do you want to know?", text: $viewModel.query, axis: .vertical)
                        .lineLimit(2...5)
                        .textFieldStyle(.roundedBorder)
                        .autocorrectionDisabled()
                        .accessibilityIdentifier("kos.ai.askInput")
                        .disabled(viewModel.aiDisabled)

                    HStack {
                        Spacer()
                        Button {
                            Task { await viewModel.ask() }
                        } label: {
                            if viewModel.isLoading {
                                ProgressView()
                            } else {
                                Text("Ask")
                                    .frame(minWidth: 80)
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(!viewModel.canSubmit)
                        .accessibilityIdentifier("kos.ai.askSend")
                    }
                }

                if let message = viewModel.errorMessage {
                    Text(message)
                        .font(.subheadline)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("kos.ai.error")
                }

                if let answer = viewModel.answer {
                    AnswerSection(answer: answer)
                }
            }
            .padding()
        }
        .navigationTitle("AI")
        .accessibilityIdentifier("kos.ai.screen")
        .task {
            viewModel.setAIDisabled(authStore.capabilities?.aiEnabled == false)
        }
        .onChange(of: authStore.capabilities?.aiEnabled) { _, newValue in
            viewModel.setAIDisabled(newValue == false)
        }
    }
}

private struct AnswerSection: View {
    let answer: AnswerResponseDTO

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Answer")
                .font(.subheadline.weight(.semibold))
            Text(answer.answer)
                .font(.body)
                .accessibilityIdentifier("kos.ai.answerText")

            if let warning = answer.warning, !warning.isEmpty {
                Text(warning)
                    .font(.caption)
                    .foregroundStyle(.orange)
            }

            if !answer.citations.isEmpty {
                Divider()
                Text("Citations")
                    .font(.subheadline.weight(.semibold))
                ForEach(answer.citations, id: \.objectId) { citation in
                    NavigationLink(value: ObjectRoute(id: citation.objectId, kind: citation.kind)) {
                        CitationRow(citation: citation)
                    }
                    .buttonStyle(.plain)
                }
            }

            if !answer.webCitations.isEmpty {
                Divider()
                Text("Web citations")
                    .font(.subheadline.weight(.semibold))
                ForEach(answer.webCitations, id: \.url) { web in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(web.title).font(.subheadline)
                        if let url = URL(string: web.url) {
                            Link(web.url, destination: url)
                                .font(.caption)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
