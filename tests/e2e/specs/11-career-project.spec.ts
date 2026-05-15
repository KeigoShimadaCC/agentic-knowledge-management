import type { APIRequestContext } from "@playwright/test";

import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

async function createProject(api: APIRequestContext, title: string) {
  const response = await api.post("/api/v1/projects", {
    data: {
      title,
      role: "Lead Engineer",
      organization: "Acme",
      problem: "Knowledge was fragmented.",
      actions: "Built ingestion and search.",
      results: "Reduced lookup time.",
      skills: ["python"],
      metrics: { impact: "40%" },
    },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as { id: string; title: string };
}

test.describe("Career project golden path", () => {
  test("create project and view in list", async ({ page }) => {
    await page.goto("/app/projects");
    await page.getByRole("button", { name: "New project" }).click();
    await page.getByLabel("Title").fill("KnowledgeOS v1");
    await page.getByRole("button", { name: "Save" }).click();

    await page.goto("/app/projects");
    await expect(page.getByText("KnowledgeOS v1")).toBeVisible();
  });

  test("link evidence to project", async ({ page, api }) => {
    const project = await createProject(api, `Evidence project ${crypto.randomUUID()}`);
    const pageId = await createPage(api, "Evidence page", "Evidence about the project.");
    await page.route("**/api/v1/search/hybrid", async (route) => {
      await route.fulfill({
        json: {
          results: [
            {
              id: pageId,
              kind: "page",
              title: "Evidence page",
              snippet: null,
              tags: [],
              score: 1,
              keyword_score: 1,
              vector_score: 0,
              recency_boost: 0,
              updated_at: new Date().toISOString(),
              source_type: null,
              ingestion_status: null,
            },
          ],
          total: 1,
          query: "evidence",
          mode: "hybrid",
          embeddings_used: false,
        },
      });
    });

    await page.goto(`/app/projects/${project.id}`);
    await page.getByRole("button", { name: "Evidence" }).click();
    await page.getByRole("button", { name: "Link evidence" }).click();
    await page.getByPlaceholder("Search pages, sources, or chats").fill("evidence");
    await page.getByText("Evidence page").click();

    await expect(page.getByText("Evidence page")).toBeVisible();
  });

  test("generate and save resume bullets", async ({ page, api }) => {
    const project = await createProject(api, `Bullet project ${crypto.randomUUID()}`);
    await page.route("**/api/v1/ai/generate-resume-bullets", async (route) => {
      await route.fulfill({
        json: {
          project_id: project.id,
          agent_run_id: crypto.randomUUID(),
          evidence_count: 0,
          bullets: [
            {
              text: "Built KnowledgeOS project memory and reduced lookup time by 40%.",
              evidence_object_ids: [],
              confidence: "high",
              metrics_cited: ["40%"],
            },
          ],
        },
      });
    });

    await page.goto(`/app/projects/${project.id}`);
    await page.getByRole("button", { name: "Resume Bullets" }).click();
    await page.getByRole("button", { name: "Generate" }).click();
    await expect(page.getByText(/Built KnowledgeOS project memory/)).toBeVisible();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText(/Staff Engineer · 1 bullets/)).toBeVisible();
  });

  test("markdown export triggers download", async ({ page, api }) => {
    const project = await createProject(api, `Export project ${crypto.randomUUID()}`);
    await page.goto(`/app/projects/${project.id}`);

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Download Markdown" }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.md$/);
  });
});
