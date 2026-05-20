import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { addUserCookie, createTestUser } from "../fixtures/test-user";

const TAG = `sai03-${Date.now().toString(36)}`;
const CONTENT =
  "Q3 planning meeting. We decided to focus on three key initiatives: improving user onboarding flow, reducing API response times by 40%, and launching the mobile app by end of quarter. The onboarding redesign will require coordination with design team. API optimization needs backend work on database queries. Mobile launch depends on completing the authentication module.";

let inboxItemTitle = "";
let inboxObjectId = "";
let seedApi: APIRequestContext;
let savedCookie = "";

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

async function openTriageModal(page: Page) {
  await page.goto("/app/inbox");
  await page.getByText(inboxItemTitle, { exact: false }).first().waitFor({ timeout: 10_000 });
  // Use span.truncate to find the exact row, avoiding matches on parent containers
  const row = page
    .locator('[class*="rounded-lg"][class*="border"][class*="bg-gray-900"]')
    .filter({ has: page.locator("span.truncate", { hasText: inboxItemTitle }) })
    .first();
  await row.getByRole("button", { name: /triage/i }).click();
  await expect(page.getByTestId("triage-modal")).toBeVisible({ timeout: 5_000 });
}

test.describe.configure({ mode: "serial", timeout: 60_000 });

test.describe("SAI03 inbox triage", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    savedCookie = user.cookie;
    inboxItemTitle = `Q3 Planning ${TAG}`;
    const res = await seedApi.post("/api/v1/pages", { data: { title: inboxItemTitle } });
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as { object: { id: string }; page: { id: string } };
    inboxObjectId = body.object.id;

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
    // Do NOT add tags — inbox only shows objects with tags == []
  });

  test.beforeEach(async ({ context }) => {
    await addUserCookie(context, savedCookie);
  });

  test.afterAll(async () => {
    if (inboxObjectId) {
      await seedApi.delete(`/api/v1/objects/${inboxObjectId}`);
    }
    await seedApi.dispose();
  });

  test("@sai03 inbox shows the seeded item", async ({ page }) => {
    await page.goto("/app/inbox");
    await expect(page.getByText(inboxItemTitle, { exact: false })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("@sai03 triage modal opens", async ({ page }) => {
    await openTriageModal(page);
  });

  test("@sai03 analyze with AI returns real summary", async ({ page }) => {
    await openTriageModal(page);
    const triagePromise = page.waitForResponse(
      (r) => r.url().includes("/api/v1/ai/triage"),
      { timeout: 15_000 }
    );
    await page.getByRole("button", { name: "Analyze with AI" }).click();
    const response = await triagePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { summary: string; suggested_tags: string[] };
    expect(body.summary.length).toBeGreaterThan(30);
    expect(body.suggested_tags.length).toBeGreaterThanOrEqual(1);
    await expect(page.getByTestId("triage-modal").getByText(/.{20,}/).first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("@sai03 applying suggested tags closes modal", async ({ page }) => {
    await openTriageModal(page);
    const triagePromise = page.waitForResponse((r) => r.url().includes("ai/triage"), {
      timeout: 15_000,
    });
    await page.getByRole("button", { name: "Analyze with AI" }).click();
    await triagePromise;
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(page.getByTestId("triage-modal")).not.toBeVisible({ timeout: 5_000 });
  });

  test("@sai03 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/inbox");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
