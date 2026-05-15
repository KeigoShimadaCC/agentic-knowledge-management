import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

test("shows the AI summarize disabled state when no local OpenAI key is configured", async ({
  page,
  api,
}) => {
  const title = `AI summary ${crypto.randomUUID()}`;
  const pageId = await createPage(api, title, "KnowledgeOS keeps AI disabled without a key.");

  await page.goto(`/app/pages/${pageId}`);
  await page.getByRole("button", { name: "AI" }).click();
  await page.getByRole("button", { name: "Summarize" }).click();

  await expect(page.getByText("ai_disabled")).toBeVisible({ timeout: 5_000 });
});

