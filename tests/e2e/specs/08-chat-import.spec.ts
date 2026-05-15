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
  await page.locator("select").first().selectOption("claude");
  await page.getByPlaceholder("Optional").fill(title);
  await page.locator("select").nth(1).selectOption("md");
  await page.locator("textarea").fill(transcript);
  await page.getByRole("button", { name: "Import Transcript" }).click();

  await expect(page).toHaveURL(/\/app\/chats\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await expect(page.getByText("2 turns")).toBeVisible();
  await expect(page.getByText(`Capture the testing plan for ${marker}.`)).toBeVisible();
});
