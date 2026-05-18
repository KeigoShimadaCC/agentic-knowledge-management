import Foundation

/// Central registry of accessibility identifiers for Simulator MCP / UI tests.
/// Convention: `kos.<screen>.<element>` — use these constants in SwiftUI views.
enum Kos {
    enum Connect {
        static let screen = "kos.connect.screen"
        static let urlField = "kos.connect.urlField"
        static let testConnectionButton = "kos.connect.testConnectionButton"
        static let statusIdle = "kos.connect.status.idle"
        static let statusLoading = "kos.connect.status.loading"
        static let statusSuccess = "kos.connect.status.success"
        static let statusFailure = "kos.connect.status.failure"
    }

    enum Login {
        static let screen = "kos.login.screen"
        static let emailField = "kos.login.emailField"
        static let passwordField = "kos.login.passwordField"
        static let submitButton = "kos.login.submitButton"
        static let errorBanner = "kos.login.errorBanner"
    }

    enum Home {
        static let screen = "kos.home.screen"
        static let placeholder = "kos.home.placeholder"
        static let recentList = "kos.home.recentList"
        static let captureButton = "kos.home.captureButton"
    }

    enum Search {
        static let screen = "kos.search.screen"
        static let input = "kos.search.input"
        static let submitButton = "kos.search.submitButton"
        static let resultsList = "kos.search.resultsList"
        static let resultRow = "kos.search.resultRow"
    }

    enum Capture {
        static let entry = "kos.capture.entry"
        static let screen = "kos.capture.screen"
        static let titleField = "kos.capture.titleField"
        static let noteField = "kos.capture.noteField"
        static let pasteButton = "kos.capture.pasteButton"
        static let saveButton = "kos.capture.saveButton"
        static let successLink = "kos.capture.successLink"
    }

    enum Upload {
        static let screen = "kos.upload.screen"
        static let photoButton = "kos.upload.photoButton"
        static let pickButton = "kos.upload.pickButton"
        static let statusLabel = "kos.upload.statusLabel"
        static let retryButton = "kos.upload.retryButton"
    }

    enum AI {
        static let screen = "kos.ai.screen"
        static let questionField = "kos.ai.questionField"
        static let askButton = "kos.ai.askButton"
        static let answerText = "kos.ai.answerText"
    }

    enum Settings {
        static let screen = "kos.settings.screen"
        static let logoutButton = "kos.settings.logoutButton"
        static let workspacesLink = "kos.settings.workspacesLink"
        static let chatsLink = "kos.settings.chatsLink"
        static let projectsLink = "kos.settings.projectsLink"
        static let trashLink = "kos.settings.trashLink"
    }

    enum ObjectDetail {
        static let editButton = "kos.objectDetail.editButton"
        static let tagsRow = "kos.objectDetail.tagsRow"
    }

    enum PageDetail {
        static let editButton = "kos.pageDetail.editButton"
    }

    enum EditMetadata {
        static let screen = "kos.editMetadata.screen"
        static let titleField = "kos.editMetadata.titleField"
        static let tagField = "kos.editMetadata.tagField"
        static let tagChip = "kos.editMetadata.tagChip"
        static let tagAddButton = "kos.editMetadata.tagAddButton"
        static let saveButton = "kos.editMetadata.saveButton"
        static let cancelButton = "kos.editMetadata.cancelButton"
        static let errorBanner = "kos.editMetadata.errorBanner"
    }

    enum EditBody {
        static let screen = "kos.editBody.screen"
        static let editor = "kos.editBody.editor"
        static let saveButton = "kos.editBody.saveButton"
        static let cancelButton = "kos.editBody.cancelButton"
        static let errorBanner = "kos.editBody.errorBanner"
    }

    enum Conflict {
        static let screen = "kos.conflict.screen"
        static let discardButton = "kos.conflict.discardButton"
        static let keepMineButton = "kos.conflict.keepMineButton"
    }

    enum Trash {
        static let screen = "kos.trash.screen"
        static let list = "kos.trash.list"
        static let restoreButton = "kos.trash.restoreButton"
    }

    enum Workspace {
        static let listScreen = "kos.workspace.list.screen"
        static let list = "kos.workspace.list"
        static let detailScreen = "kos.workspace.detail.screen"
        static let editButton = "kos.workspace.editButton"
        static let nameField = "kos.workspace.nameField"
        static let descriptionField = "kos.workspace.descriptionField"
        static let pinnedToggle = "kos.workspace.pinnedToggle"
        static let saveButton = "kos.workspace.saveButton"
    }

    enum Graph {
        static let section = "kos.graph.section"
        static let linkButton = "kos.graph.linkButton"
        static let unlinkButton = "kos.graph.unlinkButton"
        static let linkSheet = "kos.graph.linkSheet"
        static let searchField = "kos.graph.searchField"
        static let kindPicker = "kos.graph.kindPicker"
        static let createButton = "kos.graph.createButton"
    }

    enum Project {
        static let listScreen = "kos.project.list.screen"
        static let list = "kos.project.list"
        static let editButton = "kos.project.editButton"
        static let titleField = "kos.project.titleField"
        static let statusPicker = "kos.project.statusPicker"
        static let saveButton = "kos.project.saveButton"
    }

    enum Chat {
        static let listScreen = "kos.chat.list.screen"
        static let list = "kos.chat.list"
        static let row = "kos.chat.row"
    }
}
