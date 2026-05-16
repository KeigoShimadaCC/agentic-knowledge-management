import { expect, test } from "../fixtures/api";

test("imports a Claude-format markdown chat through the paste flow", async ({ page, api: _api }) => {
  const marker = crypto.randomUUID();
  const title = `Claude import ${marker}`;
  const transcript = `# ${title}

Human: Capture the testing plan for ${marker}.

Assistant: Keep Vitest, Playwright, and worker extractor coverage in separate PRs.
`;

  await page.goto("/app/chats");
  await page.getByRole("button", { name: "Import chat" }).click();
  await page.getByRole("button", { name: "Paste Transcript" }).click();
  // Scope to the modal overlay to avoid matching the sort-order select in the toolbar
  const modal = page.locator(".fixed.inset-0").last();
  await modal.getByLabel("Provider").selectOption("claude");
  await modal.getByPlaceholder("Optional").fill(title);
  await modal.getByLabel("Format").selectOption("md");
  await modal.locator("textarea").fill(transcript);
  await modal.getByRole("button", { name: "Import Transcript" }).click();

  await expect(page).toHaveURL(/\/app\/chats\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByText("2 turns")).toBeVisible();
  await expect(page.getByText(`Capture the testing plan for ${marker}.`)).toBeVisible();
});
