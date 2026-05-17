import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { createTestUser } from "../fixtures/test-user";
import { createPage } from "../fixtures/pages";
import {
  seedSource,
  cleanupByTag,
} from "../fixtures/scenario-fixtures";

const TAG = `s04-${Date.now().toString(36)}`;
let seedApi: APIRequestContext;

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

async function tagObject(api: APIRequestContext, objectId: string) {
  const response = await api.patch(`/api/v1/objects/${objectId}`, { data: { tags: [TAG] } });
  expect(response.ok()).toBeTruthy();
}

test.describe.configure({ mode: "serial", timeout: 60_000 });
test.describe("S04 AI developer MCP scenario", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    await seedSource(seedApi, {
      title: "Model Context Protocol",
      url: "https://en.wikipedia.org/wiki/Model_Context_Protocol",
      sourceType: "web",
      tags: [TAG],
    });
    await seedSource(seedApi, {
      title: "Application Programming Interface",
      url: "https://en.wikipedia.org/wiki/API",
      sourceType: "web",
      tags: [TAG],
    });
    const pageId = await createPage(seedApi, `ADR: Auth Design ${TAG}`, `ADR: Auth Design ${TAG}`);
    await tagObject(seedApi, pageId);
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@s04 MCP settings page renders", async ({ page }) => {
    await page.goto("/app/settings/mcp");
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.getByText(/Add|Connection/i).first()).toBeVisible();
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
  });

  test("@s04 search API does not expose secrets", async ({ api }) => {
    let response = await api.post("/api/v1/search/hybrid", {
      data: { query: "test", limit: 3 },
    });
    if (!response.ok()) {
      response = await api.get("/api/v1/search/keyword?q=test&limit=3");
    }
    const text = await response.text();
    expect(text).not.toContain('"api_key"');
    expect(text).not.toContain('"session_secret"');
    expect(text).not.toContain('"password_hash"');
  });

  test("@s04 agent-created page appears in UI", async ({ page, api }) => {
    const response = await api.post("/api/v1/pages", {
      data: { title: `Agent Page ${TAG}` },
    });
    expect(response.status()).toBe(201);
    const body = (await response.json()) as { object: { id: string } };
    await tagObject(api, body.object.id);

    await page.goto("/app/pages");
    await expect(page.getByText("Agent Page", { exact: false })).toBeVisible();
  });

  test("@s04 file protocol URL rejected", async ({ api }) => {
    const response = await api.post("/api/v1/sources", {
      data: { source_type: "web", url: "file:///etc/passwd", title: "test" },
    });
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test("@s04 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/settings/mcp");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
