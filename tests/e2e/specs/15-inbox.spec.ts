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
