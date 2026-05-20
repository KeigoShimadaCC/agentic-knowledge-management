import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { cleanupByTag } from "../fixtures/scenario-fixtures";
import { addUserCookie, createTestUser } from "../fixtures/test-user";

const TAG = `sai04-${Date.now().toString(36)}`;

let context7Id = "";
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

test.describe.configure({ mode: "serial", timeout: 120_000 });

test.describe("SAI04 Context7 MCP", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    savedCookie = user.cookie;
    const connRes = await seedApi.post("/api/v1/mcp-connections/", {
      data: {
        name: "Context7",
        transport: "http",
        url: "https://mcp.context7.com/mcp",
        enabled: true,
      },
    });
    expect(connRes.ok()).toBeTruthy();
    const conn = (await connRes.json()) as { id: string };
    context7Id = conn.id;
    await seedApi.post(`/api/v1/mcp-connections/${context7Id}/test`);

    const pageRes = await seedApi.post("/api/v1/pages", {
      data: { title: `TypeScript Next.js Notes ${TAG}` },
    });
    expect(pageRes.ok()).toBeTruthy();
    const body = (await pageRes.json()) as { object: { id: string }; page: { id: string } };
    pageId = body.object.id;
    const content =
      "Setting up TypeScript in a Next.js project involves configuring tsconfig.json and installing type definitions.";
    const patchPage = await seedApi.patch(`/api/v1/pages/${body.page.id}`, {
      data: {
        content_json: {
          type: "doc",
          content: [{ type: "paragraph", content: [{ type: "text", text: content }] }],
        },
        content_text: content,
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
    if (context7Id) await seedApi.delete(`/api/v1/mcp-connections/${context7Id}`);
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@sai04 MCP settings shows Context7 connection", async ({ page }) => {
    await page.goto("/app/settings/mcp");
    await expect(page.getByText("Context7", { exact: false })).toBeVisible();
  });

  test("@sai04 connection has capabilities after test", async () => {
    await expect
      .poll(
        async () => {
          const res = await seedApi.get(`/api/v1/mcp-connections/${context7Id}`);
          expect(res.ok()).toBeTruthy();
          const body = (await res.json()) as { capabilities?: unknown[] | null };
          if ((body.capabilities?.length ?? 0) > 0) return body.capabilities?.length ?? 0;
          await seedApi.post(`/api/v1/mcp-connections/${context7Id}/test`);
          return body.capabilities?.length ?? 0;
        },
        { timeout: 30_000 }
      )
      .toBeGreaterThan(0);
  });

  test("@sai04 enrich-page pulls live docs", async ({ page }) => {
    await openAiTab(page);
    await page.getByTestId("ai-panel").getByPlaceholder(/library|topic/i).fill("TypeScript Next.js");
    const enrichPromise = page.waitForResponse((r) => r.url().includes("enrich-page"), {
      timeout: 30_000,
    });
    await page.getByTestId("ai-panel").getByRole("button", { name: "Fetch & Link Docs" }).click();
    const response = await enrichPromise;
    expect(response.status()).toBe(200);
  });

  test("@sai04 enriched sources appear in sources list", async ({ page }) => {
    await page.goto("/app/sources");
    await expect(page.getByText(/typescript|next\.?js/i).first()).toBeVisible({ timeout: 8_000 });
  });

  test("@sai04 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/settings/mcp");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
