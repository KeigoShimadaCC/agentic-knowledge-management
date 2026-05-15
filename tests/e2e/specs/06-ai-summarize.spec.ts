import { expect, test } from "../fixtures/api";
import { closeDatabase, getLatestAgentRun } from "../fixtures/db";
import { createPage } from "../fixtures/pages";

const STUB_SUMMARY = "Canned E2E summary.";

test.afterAll(async () => {
  await closeDatabase();
});

test("summarizes a page via the API stub and records an agent run audit row", async ({
  page,
  api,
  testUser,
}) => {
  const title = `AI summary ${crypto.randomUUID()}`;
  const pageId = await createPage(
    api,
    title,
    "KnowledgeOS summarizes local knowledge safely."
  );

  await page.goto(`/app/pages/${pageId}`);
  await page.getByRole("button", { name: "AI" }).click();
  await page.getByRole("button", { name: "Summarize" }).click();

  await expect(page.getByText(STUB_SUMMARY)).toBeVisible({ timeout: 15_000 });

  const agentRun = await getLatestAgentRun(testUser.id, "summarize");
  expect(agentRun, "summarize should create an agent_runs audit row").toMatchObject({
    agent_type: "summarize",
    status: "success",
  });
});
