import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { cleanupByTag } from "../fixtures/scenario-fixtures";
import { addUserCookie, createTestUser } from "../fixtures/test-user";

const TAG = `sai02-${Date.now().toString(36)}`;
const CONTENT =
  "TypeScript is a strongly typed programming language that builds on JavaScript, developed by Microsoft. It adds optional static typing and class-based object-oriented programming. TypeScript catches errors early through its type system and makes large codebases more maintainable. Anders Hejlsberg designed TypeScript in 2012. Major frameworks like Angular and NestJS use TypeScript as their primary language. TypeScript compiles to plain JavaScript and runs anywhere JavaScript runs.";

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

async function openAiTab(page: Page) {
  await page.goto(`/app/pages/${pageId}`);
  await page.getByTestId("graph-tab-ai").click();
  await expect(page.getByTestId("ai-panel")).toBeVisible();
}

test.describe.configure({ mode: "serial", timeout: 60_000 });

test.describe("SAI02 page intelligence", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    savedCookie = user.cookie;
    const res = await seedApi.post("/api/v1/pages", {
      data: { title: `TypeScript Notes ${TAG}` },
    });
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as { object: { id: string }; page: { id: string } };
    pageId = body.object.id;

    const patchPage = await seedApi.patch(`/api/v1/pages/${body.page.id}`, {
      data: {
        content_json: {
          type: "doc",
          content: [{ type: "paragraph", content: [{ type: "text", text: CONTENT }] }],
        },
        content_text: CONTENT,
      },
    });
    expect(patchPage.ok()).toBeTruthy();
    const patchObject = await seedApi.patch(`/api/v1/objects/${pageId}`, {
      data: { tags: [TAG] },
    });
    expect(patchObject.ok()).toBeTruthy();
  });

  test.beforeEach(async ({ context }) => {
    await addUserCookie(context, savedCookie);
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@sai02 page renders with content", async ({ page }) => {
    await page.goto(`/app/pages/${pageId}`);
    await expect(page.locator("main").first()).toBeVisible();
    await expect(page.getByText("TypeScript Notes", { exact: false })).toBeVisible();
  });

  test("@sai02 summarize produces a paragraph", async ({ page }) => {
    await openAiTab(page);
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("/api/v1/ai/summarize"),
      { timeout: 15_000 }
    );
    await page.getByTestId("ai-panel").getByRole("button", { name: "Summarize" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { summary: string };
    expect(body.summary.length).toBeGreaterThan(50);
    await expect(page.getByTestId("ai-panel").locator("p").first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("@sai02 extract claims produces ≥2 claims", async ({ page }) => {
    await openAiTab(page);
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("extract-claims"),
      { timeout: 15_000 }
    );
    await page.getByTestId("ai-panel").getByRole("button", { name: "Extract Claims" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { items: Array<{ title: string }> };
    expect(body.items.length).toBeGreaterThanOrEqual(2);
    await expect(page.locator('[data-testid="ai-panel"] li').first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("@sai02 claims reference TypeScript", async ({ page }) => {
    await openAiTab(page);
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("extract-claims"),
      { timeout: 15_000 }
    );
    await page.getByTestId("ai-panel").getByRole("button", { name: "Extract Claims" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { items: Array<{ title: string }> };
    expect(body.items.some((item) => /typescript/i.test(item.title))).toBe(true);
  });

  test("@sai02 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/pages");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
