import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_WEB_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  // workers: 1 everywhere — two workers share a single Postgres + worker + qdrant
  // stack, so cross-worker writes race the per-test reads (worker B reads /app/inbox
  // before worker A's seed lands). 109/123 passing with workers:2 had three CI-only
  // flakes that vanished under serial execution.
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: "node -e \"setInterval(() => {}, 1 << 30)\"",
    url: baseURL,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
