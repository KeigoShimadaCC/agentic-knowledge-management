import { expect, test } from "../fixtures/api";

async function seedInboxItem(api: import("@playwright/test").APIRequestContext, title: string) {
  const response = await api.post("/api/v1/pages", {
    data: { title, content: `{"type":"doc","content":[]}` },
  });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { object: { id: string } };
  return body.object.id;
}

test("inbox list renders items", async ({ page, api }) => {
  const title = `Inbox item ${crypto.randomUUID()}`;
  await seedInboxItem(api, title);

  await page.goto("/app/inbox");
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });
});

test("per-item triage button opens AI triage modal", async ({ page, api }) => {
  const title = `Triage item ${crypto.randomUUID()}`;
  await seedInboxItem(api, title);

  await page.goto("/app/inbox");
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

  await page.getByRole("button", { name: "Triage with AI" }).first().click();
  // TriageModal should open with the item title or a modal-like overlay
  await expect(page.locator(".fixed.inset-0")).toBeVisible({ timeout: 5_000 });
});

test("triage modal shows AI summary after Analyze click", async ({ page, api }) => {
  const title = `AI triage item ${crypto.randomUUID()}`;
  const id = await seedInboxItem(api, title);

  await page.route("**/api/v1/ai/triage", async (route) => {
    await route.fulfill({
      json: {
        suggested_tags: ["engineering"],
        suggested_title: null,
        summary: "This is a triage summary from the mock.",
        agent_run_id: null,
      },
    });
  });

  await page.goto("/app/inbox");
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

  await page.getByRole("button", { name: "Triage with AI" }).first().click();
  await expect(page.locator('[data-testid="triage-modal"]')).toBeVisible({ timeout: 5_000 });

  await page.getByRole("button", { name: "Analyze with AI" }).click();
  await expect(page.getByText("This is a triage summary from the mock.")).toBeVisible({ timeout: 8_000 });
  void id;
});

test("bulk select reveals bulk action bar", async ({ page, api }) => {
  const title = `Bulk inbox ${crypto.randomUUID()}`;
  await seedInboxItem(api, title);

  await page.goto("/app/inbox");
  await expect(page.getByText(title)).toBeVisible({ timeout: 8_000 });

  const checkbox = page.getByRole("checkbox", { name: new RegExp(title) });
  await expect(checkbox).toBeVisible();
  await checkbox.check();

  await expect(page.getByText(/\d+ selected/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Auto-triage selected/ })).toBeVisible();
});
