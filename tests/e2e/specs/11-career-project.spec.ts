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
    // Unique-per-run title — the DB persists projects across runs and a hard-coded
    // string accumulates duplicates that trip strict-mode locator matching.
    const title = `KnowledgeOS v1 ${crypto.randomUUID().slice(0, 8)}`;
    await page.goto("/app/projects");
    await page.getByRole("button", { name: "New project" }).click();
    await page.getByLabel("Title").fill(title);
    await page.getByRole("button", { name: "Save" }).click();

    await page.goto("/app/projects");
    await expect(page.getByText(title)).toBeVisible();
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
    const stubBullet = {
      text: "Built KnowledgeOS project memory and reduced lookup time by 40%.",
      evidence_object_ids: [],
      confidence: "high",
      metrics_cited: ["40%"],
    };

    await page.route("**/api/v1/ai/generate-resume-bullets", async (route) => {
      await route.fulfill({
        json: {
          project_id: project.id,
          // null avoids FK constraint violation: agent_run_id FK requires a real agent_runs row
          agent_run_id: null,
          evidence_count: 0,
          bullets: [stubBullet],
        },
      });
    });

    // Mock save + list so the FK null passes cleanly and UI updates deterministically
    const savedSetId = crypto.randomUUID();
    const savedSet = {
      id: savedSetId,
      user_id: crypto.randomUUID(),
      project_id: project.id,
      target_role: "Lead Engineer",
      emphasis: null,
      count: 1,
      bullets: [stubBullet],
      agent_run_id: null,
      prompt_version: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      deleted_at: null,
    };
    await page.route(`**/api/v1/projects/${project.id}/resume-bullet-sets`, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ status: 201, contentType: "application/json", json: savedSet });
      } else {
        await route.fulfill({ json: [savedSet] });
      }
    });

    await page.goto(`/app/projects/${project.id}`);
    await page.getByRole("button", { name: "Resume Bullets" }).click();
    await page.getByRole("button", { name: "Generate" }).click();
    await expect(page.getByText(/Built KnowledgeOS project memory/)).toBeVisible();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText(/Lead Engineer · 1 bullets/)).toBeVisible({ timeout: 10_000 });
  });

  test("copy markdown shows Copied toast", async ({ page, api }) => {
    const project = await createProject(api, `Copy bullet project ${crypto.randomUUID()}`);
    const stubBullet = {
      text: "Built KnowledgeOS project memory and reduced lookup time by 40%.",
      evidence_object_ids: [],
      confidence: "high",
      metrics_cited: ["40%"],
    };

    await page.route("**/api/v1/ai/generate-resume-bullets", async (route) => {
      await route.fulfill({
        json: {
          project_id: project.id,
          agent_run_id: null,
          evidence_count: 0,
          bullets: [stubBullet],
        },
      });
    });

    const savedSetId = crypto.randomUUID();
    const savedSet = {
      id: savedSetId,
      user_id: crypto.randomUUID(),
      project_id: project.id,
      target_role: "Lead Engineer",
      emphasis: null,
      count: 1,
      bullets: [stubBullet],
      agent_run_id: null,
      prompt_version: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      deleted_at: null,
    };
    await page.route(`**/api/v1/projects/${project.id}/resume-bullet-sets`, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ status: 201, contentType: "application/json", json: savedSet });
      } else {
        await route.fulfill({ json: [savedSet] });
      }
    });

    // Grant clipboard permissions so clipboard.writeText doesn't throw
    await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);

    await page.goto(`/app/projects/${project.id}`);
    await page.getByRole("button", { name: "Resume Bullets" }).click();
    await page.getByRole("button", { name: "Generate" }).click();
    await expect(page.getByText(/Built KnowledgeOS project memory/)).toBeVisible();
    await page.getByRole("button", { name: "Save" }).click();

    // Expand the saved set
    await expect(page.getByText(/Lead Engineer · 1 bullets/)).toBeVisible({ timeout: 10_000 });
    await page.getByText(/Lead Engineer · 1 bullets/).click();

    // Click Copy Markdown and assert the toast
    await page.getByRole("button", { name: "Copy Markdown" }).click();
    await expect(page.getByText("Copied")).toBeVisible({ timeout: 5_000 });
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
