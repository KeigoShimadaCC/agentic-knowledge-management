import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

async function openAiPanel(
  page: import("@playwright/test").Page,
  api: import("@playwright/test").APIRequestContext
) {
  const id = await createPage(api, `AI advanced ${crypto.randomUUID()}`, "Test content for AI panel.");
  await page.goto(`/app/pages/${id}`);
  await page.getByTestId("graph-tab-ai").click();
  await expect(page.getByText("Summarize").first()).toBeVisible();
  return id;
}

test("Extract Claims button is visible in AI panel", async ({ page, api }) => {
  await openAiPanel(page, api);
  await expect(page.getByRole("button", { name: "Extract Claims" })).toBeVisible();
});

test("Extract Tasks button is visible in AI panel", async ({ page, api }) => {
  await openAiPanel(page, api);
  await expect(page.getByRole("button", { name: "Extract Tasks" })).toBeVisible();
});

test("Suggest Links button is visible in AI panel", async ({ page, api }) => {
  await openAiPanel(page, api);
  await expect(page.getByRole("button", { name: "Suggest Links" })).toBeVisible();
});

test("Ask KB input renders with placeholder text", async ({ page, api }) => {
  await openAiPanel(page, api);
  await expect(page.getByPlaceholder("Ask a question…")).toBeVisible();
});

test("Enrich with Docs input renders", async ({ page, api }) => {
  await openAiPanel(page, api);
  await expect(page.getByPlaceholder("Library or topic…")).toBeVisible();
});

test("Extract Claims shows loading state on click (mocked)", async ({ page, api }) => {
  const id = await createPage(api, `Claims test ${crypto.randomUUID()}`, "Content with claims.");

  await page.route("**/api/v1/ai/extract-claims", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      json: {
        items: [{ id: crypto.randomUUID(), title: "KnowledgeOS runs locally." }],
        agent_run_id: null,
      },
    });
  });

  await page.goto(`/app/pages/${id}`);
  await page.getByTestId("graph-tab-ai").click();
  await page.getByRole("button", { name: "Extract Claims" }).click();
  await expect(page.getByText("KnowledgeOS runs locally.")).toBeVisible({ timeout: 8_000 });
});

test("Ask KB web search toggle renders checkbox", async ({ page, api }) => {
  await openAiPanel(page, api);
  // The checkbox is inside the Ask KB section
  await expect(page.getByText("Search web if KB has no match")).toBeVisible();
});
