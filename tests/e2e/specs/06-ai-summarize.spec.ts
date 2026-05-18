import { expect, test } from "../fixtures/api";
import { closeDatabase, getLatestAgentRun } from "../fixtures/db";
import { createPage } from "../fixtures/pages";

// The stub provider in services/api/app/ai/providers.py returns text that
// CONTAINS this substring for the "summarize" agent_type, so the page-level
// text assertion below stays meaningful without bypassing the real backend.
const STUB_SUMMARY_SUBSTRING = "Canned E2E summary.";

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

  // No browser-level page.route stub: the providers.py OPENAI_TEST_STUB_KEY
  // short-circuit (CI sets OPENAI_API_KEY=sk-test-stub) already returns canned
  // text without calling OpenAI. Intercepting at the browser would skip the
  // real backend and the agent_runs row that this test asserts on below.
  await page.goto(`/app/pages/${pageId}`);
  await page.getByRole("button", { name: "AI" }).click();
  await page.getByRole("button", { name: "Summarize" }).click();

  await expect(page.getByText(STUB_SUMMARY_SUBSTRING)).toBeVisible({ timeout: 15_000 });

  const agentRun = await getLatestAgentRun(testUser.id, "summarize");
  expect(agentRun, "summarize should create an agent_runs audit row").toMatchObject({
    agent_type: "summarize",
    status: "success",
  });
});
