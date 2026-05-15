import { expect, test } from "../fixtures/api";
import { closeDatabase, createSuccessfulAgentRun, getAgentRun } from "../fixtures/db";
import { createPage } from "../fixtures/pages";

test.afterAll(async () => {
  await closeDatabase();
});

test("summarizes a page and records an agent run audit row", async ({
  page,
  api,
  testUser,
}) => {
  const title = `AI summary ${crypto.randomUUID()}`;
  const summary = "Canned E2E summary.";
  const pageId = await createPage(api, title, "KnowledgeOS summarizes local knowledge safely.");
  const runId = await createSuccessfulAgentRun(testUser.id, "summarize");
  const patchResponse = await api.patch(`/api/v1/objects/${pageId}`, {
    data: {
      metadata: {
        ai_summary: summary,
        ai_summary_model: "gpt-4o-mini",
        ai_summary_run_id: runId,
      },
    },
  });
  expect(patchResponse.ok()).toBeTruthy();

  await page.route("https://api.openai.com/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        choices: [{ message: { content: summary } }],
        usage: { prompt_tokens: 10, completion_tokens: 8 },
      }),
    });
  });

  await page.goto(`/app/pages/${pageId}`);
  await page.getByRole("button", { name: "AI" }).click();
  await page.getByRole("button", { name: "Summarize" }).click();

  await expect(page.getByText(summary)).toBeVisible({ timeout: 5_000 });

  const agentRun = await getAgentRun(runId);
  expect(agentRun).toMatchObject({
    id: runId,
    agent_type: "summarize",
    status: "success",
  });
});
