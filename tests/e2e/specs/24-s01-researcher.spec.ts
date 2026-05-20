import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { addUserCookie, createTestUser } from "../fixtures/test-user";
import { createPage } from "../fixtures/pages";
import {
  seedSource,
  waitForSource,
  cleanupByTag,
} from "../fixtures/scenario-fixtures";

const TAG = `s01-${Date.now().toString(36)}`;
const SOURCES = [
  {
    url: "https://en.wikipedia.org/wiki/Attention_(machine_learning)",
    title: "Attention ML",
  },
  {
    url: "https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)",
    title: "Transformer Architecture",
  },
  {
    url: "https://en.wikipedia.org/wiki/Natural_language_processing",
    title: "Natural Language Processing",
  },
];

let firstSourceId = "";
let pageId = "";
let seedApi: APIRequestContext;
let savedCookie = "";

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

async function tagObject(api: APIRequestContext, objectId: string) {
  const response = await api.patch(`/api/v1/objects/${objectId}`, { data: { tags: [TAG] } });
  expect(response.ok()).toBeTruthy();
}

test.describe.configure({ mode: "serial", timeout: 120_000 });
test.describe("S01 researcher scenario", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    savedCookie = user.cookie;
    const sourceIds: string[] = [];
    for (const source of SOURCES) {
      sourceIds.push(await seedSource(seedApi, { ...source, sourceType: "web", tags: [TAG] }));
    }
    firstSourceId = sourceIds[0] ?? "";
    pageId = await createPage(
      seedApi,
      `Attention Mechanisms Notes ${TAG}`,
      `Attention Mechanisms Notes ${TAG}`
    );
    await tagObject(seedApi, pageId);

    for (const sourceId of sourceIds) {
      await waitForSource(seedApi, sourceId, 60_000);
    }
  });

  test.beforeEach(async ({ context }) => {
    // Scenario specs run their own login in beforeAll. The browser context needs
    // the same session cookie so its requests resolve to the demo user that owns
    // the seeded data; otherwise they fall through to the desktop single-user
    // fallback and see a different user.
    await addUserCookie(context, savedCookie);
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@s01 sources list shows seeded sources", async ({ page }) => {
    await page.goto("/app/sources");
    await expect(page.locator("aside").first()).toBeVisible();
    for (const source of SOURCES) {
      await expect(page.getByText(source.title, { exact: false })).toBeVisible();
    }
  });

  test("@s01 source detail renders without crash", async ({ page }) => {
    await page.goto(`/app/sources/${firstSourceId}`);
    await expect(page).toHaveURL(/\/sources\//);
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
  });

  test("@s01 notes page is visible in pages list", async ({ page }) => {
    await page.goto("/app/pages");
    await expect(page.getByText("Attention Mechanisms Notes", { exact: false })).toBeVisible();
    expect(pageId).toBeTruthy();
  });

  test("@s01 search returns results for seeded content", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app");
    await openSearch(page);
    await page.getByPlaceholder(/search knowledge base/i).fill("attention");
    await page.waitForTimeout(2_000);
    await expectSearchResults(page);
    expect(errors).toEqual([]);
  });

  test("@s01 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
