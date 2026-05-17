import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { createTestUser } from "../fixtures/test-user";
import {
  seedSource,
  waitForSource,
  cleanupByTag,
} from "../fixtures/scenario-fixtures";

const TAG = `s05-${Date.now().toString(36)}`;
let seedApi: APIRequestContext;
const SOURCES = [
  { url: "https://en.wikipedia.org/wiki/JavaScript", title: "JavaScript" },
  { url: "https://en.wikipedia.org/wiki/Asynchronous_I/O", title: "Async IO" },
  { url: "https://en.wikipedia.org/wiki/Closure_(computer_programming)", title: "Closures" },
];

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

async function openSearch(page: Page) {
  const trigger = page.getByRole("button", { name: /search/i }).first();
  if (await trigger.isVisible().catch(() => false)) {
    await trigger.click();
  } else {
    await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  }
  await expect(page.getByPlaceholder(/search knowledge base/i)).toBeVisible();
}

async function expectSearchResults(page: Page) {
  const modal = page.locator(".fixed.inset-0").last();
  await expect(modal.getByText(/[1-9]\d* results?/i)).toBeVisible({ timeout: 10_000 });
}

test.describe.configure({ mode: "serial", timeout: 90_000 });
test.describe("S05 bootcamp grad scenario", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    const sourceIds: string[] = [];
    for (const source of SOURCES) {
      sourceIds.push(await seedSource(seedApi, { ...source, sourceType: "web", tags: [TAG] }));
    }
    for (const sourceId of sourceIds) {
      await waitForSource(seedApi, sourceId, 60_000);
    }
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@s05 sources list shows seeded sources", async ({ page }) => {
    await page.goto("/app/sources");
    await expect(page.getByText(/JavaScript|Closures/).first()).toBeVisible();
  });

  test("@s05 search finds seeded content", async ({ page }) => {
    await page.goto("/app");
    await openSearch(page);
    await page.getByPlaceholder(/search knowledge base/i).fill("javascript");
    await expectSearchResults(page);
  });

  test("@s05 inbox renders without crash", async ({ page }) => {
    await page.goto("/app/inbox");
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
  });

  test("@s05 can create project", async ({ page }) => {
    const title = `Portfolio: Todo App ${TAG}`;
    await page.goto("/app/projects");
    await page.getByRole("button", { name: "New project" }).click();
    await page.getByLabel("Title").fill(title);
    await page.getByPlaceholder("Type and press Enter").nth(1).fill(TAG);
    await page.getByPlaceholder("Type and press Enter").nth(1).press("Enter");
    await page.getByRole("button", { name: "Save" }).click();

    await page.goto("/app/projects");
    await expect(page.getByText(title)).toBeVisible();
  });

  test("@s05 graceful offline behavior", async ({ page }) => {
    await page.goto("/app/pages");
    await page.context().setOffline(true);
    await page.goto("/app").catch(() => {});
    await expect(page.locator("body")).toBeVisible();
    await page.context().setOffline(false);
  });

  test("@s05 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/sources");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
