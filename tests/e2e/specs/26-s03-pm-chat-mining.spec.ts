import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { createTestUser } from "../fixtures/test-user";
import {
  importChats,
  cleanupByTag,
} from "../fixtures/scenario-fixtures";

const TAG = `s03-${Date.now().toString(36)}`;

let firstChatId = "";
let seedApi: APIRequestContext;

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

test.describe.configure({ mode: "serial", timeout: 90_000 });
test.describe("S03 PM chat mining scenario", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    const chatData = JSON.parse(
      readFileSync(path.join(__dirname, "../fixtures/seed-data/chats/synthetic-chatgpt.json"), "utf-8")
    ) as { conversations: unknown[] };
    const chatIds = await importChats(seedApi, { conversations: chatData.conversations.slice(0, 5) });
    firstChatId = chatIds[0] ?? "";
    for (const chatId of chatIds) {
      await tagObject(seedApi, chatId);
    }
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@s03 chats list shows imported conversations", async ({ page }) => {
    await page.goto("/app/chats");
    await expect(page.locator('a[href^="/app/chats/"]').first()).toBeVisible({ timeout: 8_000 });
  });

  test("@s03 chat detail renders human-readable content", async ({ page }) => {
    await page.goto(`/app/chats/${firstChatId}`);
    const bodyText = await page.locator("main").first().innerText();
    expect(bodyText).not.toContain('"content_type"');
    expect(bodyText).not.toContain('"mapping"');
  });

  test("@s03 search finds chat content", async ({ page }) => {
    await page.goto("/app");
    await openSearch(page);
    await page.getByPlaceholder(/search knowledge base/i).fill("pricing strategy");
    await expectSearchResults(page);
  });

  test("@s03 inbox page renders", async ({ page }) => {
    await page.goto("/app/inbox");
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
  });

  test("@s03 workspace multi-pane opens", async ({ page }) => {
    await page.goto("/app");
    await openSearch(page);
    await page.getByPlaceholder(/search knowledge base/i).fill("pricing strategy");
    await expect(page.getByTitle("Open in side pane").or(page.getByRole("button", { name: "Side pane" })).first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
  });

  test("@s03 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/chats");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
