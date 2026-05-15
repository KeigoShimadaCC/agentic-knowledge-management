import { expect, test } from "../fixtures/api";

test("edits a page title and content, autosaves, and persists after reload", async ({ page, api }) => {
  const created = await api.post("/api/v1/pages", { data: { title: "Draft E2E Page" } });
  expect(created.ok()).toBeTruthy();
  const body = (await created.json()) as { object: { id: string } };

  await page.goto(`/app/pages/${body.object.id}`);
  await page.locator('h1[contenteditable="true"]').fill("Persisted E2E Page");
  await page.locator('h1[contenteditable="true"]').blur();

  const editor = page.locator(".ProseMirror");
  const saveResponse = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/v1/pages/${body.object.id}`) &&
      response.request().method() === "PATCH",
    { timeout: 5_000 }
  );
  await editor.fill("Autosaved body from Playwright");

  await saveResponse;
  await page.reload();

  await expect(page.getByRole("heading", { name: "Persisted E2E Page" })).toBeVisible();
  await expect(page.getByText("Autosaved body from Playwright")).toBeVisible();
});
