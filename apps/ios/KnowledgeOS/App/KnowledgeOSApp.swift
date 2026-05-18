import BackgroundTasks
import SwiftUI

enum BackgroundTaskIdentifiers {
    static let refresh = "com.knowledgeos.ios.syncqueue.refresh"
    static let processing = "com.knowledgeos.ios.syncqueue.processing"
}

@MainActor
final class AppDependencies {
    let networkMonitor = NetworkMonitor()
    let apiClient: APIClient
    let authStore: AuthStore
    let cacheStore: any CacheStore
    let queueStore: any QueueStore
    let cachedReadAPI: CachedReadAPI
    let queueDrainer: QueueDrainer

    init() {
        apiClient = APIClient(networkMonitor: networkMonitor)
        authStore = AuthStore(apiClient: apiClient)

        // Cache remains purgeable under Library/Caches. Pending uploads use the
        // SystemQueueStore default under Application Support so iOS does not evict them.
        if let cache = try? SystemCacheStore(db: SQLiteDatabase()),
           let queue = try? SystemQueueStore() {
            cacheStore = cache
            queueStore = queue
        } else {
            cacheStore = InMemoryCacheStore()
            queueStore = (try? SystemQueueStore()) ?? Self.makeFallbackQueue()
        }

        cachedReadAPI = CachedReadAPI(cache: cacheStore)
        queueDrainer = QueueDrainer(queue: queueStore, apiClient: apiClient)

        if ProcessInfo.processInfo.arguments.contains("-ui-testing-reset") {
            ServerConfig.shared.reset()
            try? SystemKeychainStore().deleteToken()
            try? cacheStore.clearAll()
        }

        // Skip BGTaskScheduler in the XCTest host — the scheduler's
        // permitted-identifiers entitlement may not be wired up under unit-test
        // injection and registering there can abort the process.
        if !Self.isUnitTestRun() {
            registerBackgroundTasks()
        }
    }

    private static func isUnitTestRun() -> Bool {
        NSClassFromString("XCTestCase") != nil
            || ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil
    }

    /// Reachability change handler: drain the queue when network returns. Bound to the
    /// `NetworkMonitor.$isReachable` publisher in `KnowledgeOSApp.body`.
    func handleReachabilityChange(isReachable: Bool) {
        guard isReachable else { return }
        Task.detached(priority: .utility) { [self] in
            _ = await queueDrainer.drain()
        }
    }

    func scheduleBackgroundDrains() {
        let refresh = BGAppRefreshTaskRequest(identifier: BackgroundTaskIdentifiers.refresh)
        refresh.earliestBeginDate = Date().addingTimeInterval(60)
        try? BGTaskScheduler.shared.submit(refresh)

        let processing = BGProcessingTaskRequest(identifier: BackgroundTaskIdentifiers.processing)
        processing.requiresNetworkConnectivity = true
        processing.requiresExternalPower = false
        processing.earliestBeginDate = Date().addingTimeInterval(15 * 60)
        try? BGTaskScheduler.shared.submit(processing)
    }

    private func registerBackgroundTasks() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: BackgroundTaskIdentifiers.refresh,
            using: nil
        ) { [weak self] task in
            guard let self else { task.setTaskCompleted(success: false); return }
            self.handleRefresh(task: task as! BGAppRefreshTask)
        }

        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: BackgroundTaskIdentifiers.processing,
            using: nil
        ) { [weak self] task in
            guard let self else { task.setTaskCompleted(success: false); return }
            self.handleProcessing(task: task as! BGProcessingTask)
        }
    }

    private func handleRefresh(task: BGAppRefreshTask) {
        scheduleBackgroundDrains() // re-arm
        let work = Task.detached(priority: .utility) { [self] in
            let deadline = Date().addingTimeInterval(25)
            let summary = await queueDrainer.drain(deadline: deadline)
            await MainActor.run {
                task.setTaskCompleted(success: summary.failed == 0)
            }
        }
        task.expirationHandler = { work.cancel() }
    }

    private func handleProcessing(task: BGProcessingTask) {
        scheduleBackgroundDrains() // re-arm
        let work = Task.detached(priority: .utility) { [self] in
            let summary = await queueDrainer.drain()
            await MainActor.run {
                task.setTaskCompleted(success: summary.failed == 0)
            }
        }
        task.expirationHandler = { work.cancel() }
    }

    private static func makeFallbackQueue() -> any QueueStore {
        // If even the on-disk queue fails, surface an in-memory queue so the app
        // doesn't crash. Failed captures will only persist for this session.
        InMemoryQueueStore()
    }
}

@main
struct KnowledgeOSApp: App {
    @StateObject private var appState = AppState()
    @State private var dependencies = AppDependencies()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView(authStore: dependencies.authStore)
                .environmentObject(appState)
                .environment(dependencies.authStore)
                .environment(\.appDependencies, dependencies)
                .onAppear {
                    appState.onBaseURLWillChange = { oldURL, newURL in
                        dependencies.authStore.onBaseURLChanged(from: oldURL, to: newURL)
                    }
                }
                .task {
                    await dependencies.authStore.restoreSessionIfNeeded()
                }
                .task {
                    for await isReachable in dependencies.networkMonitor.$isReachable.values {
                        dependencies.handleReachabilityChange(isReachable: isReachable)
                    }
                }
                .onChange(of: scenePhase) { _, newPhase in
                    if newPhase == .background {
                        dependencies.scheduleBackgroundDrains()
                    }
                }
        }
    }
}
