import type { APIRequestContext } from "@playwright/test";
import { expect, test } from "../fixtures/api";

async function createProject(api: APIRequestContext) {
  const res = await api.post("/api/v1/projects", {
    data: {
      title: `AI project ${crypto.randomUUID()}`,
      role: "Lead Engineer",
      organization: "Acme",
      problem: "Problem.",
      actions: "Actions.",
      results: "Results.",
      skills: ["python"],
      metrics: {},
    },
  });
  expect(res.ok()).toBeTruthy();
  return (await res.json()) as { id: string; title: string };
}

test("interview stories tab renders with Generate button", async ({ page, api }) => {
  const project = await createProject(api);
  await page.goto(`/app/projects/${project.id}`);
  await page.getByRole("button", { name: "Interview Stories" }).click();
  await expect(page.getByRole("button", { name: "Generate" })).toBeVisible();
});

test("interview story generates and shows preview (mocked)", async ({ page, api }) => {
  const project = await createProject(api);
  const stubStory = {
    situation: "Built KnowledgeOS using a microservices approach.",
    task: "Reduce lookup time.",
    action: "Implemented microservices architecture.",
    result: "Reduced lookup time by 40%.",
    evidence_object_ids: [],
  };

  await page.route("**/api/v1/ai/generate-interview-story", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      json: {
        project_id: project.id,
        agent_run_id: null,
        question_type: "behavioral",
        story: stubStory,
        word_count: 12,
        max_words: 200,
      },
    });
  });

  await page.goto(`/app/projects/${project.id}`);
  await page.getByRole("button", { name: "Interview Stories" }).click();
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByText(/Built KnowledgeOS using/)).toBeVisible({ timeout: 10_000 });
});

test("interview story save stores the story in saved stories (mocked)", async ({ page, api }) => {
  const project = await createProject(api);
  const storyId = crypto.randomUUID();
  const stubStory = {
    situation: "Mock interview story text for the test.",
    task: "Task performed.",
    action: "Actions taken.",
    result: "Result achieved.",
    evidence_object_ids: [],
  };

  await page.route("**/api/v1/ai/generate-interview-story", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      json: {
        project_id: project.id,
        agent_run_id: null,
        question_type: "behavioral",
        story: stubStory,
        word_count: 7,
        max_words: 200,
      },
    });
  });

  const savedStory = {
    id: storyId,
    user_id: crypto.randomUUID(),
    project_id: project.id,
    question_type: "behavioral",
    target_role: "Lead Engineer",
    story: stubStory,
    word_count: 7,
    max_words: 200,
    agent_run_id: null,
    prompt_version: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    deleted_at: null,
  };

  await page.route(`**/api/v1/projects/${project.id}/interview-stories`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 201, contentType: "application/json", json: savedStory });
    } else {
      await route.fulfill({ json: [savedStory] });
    }
  });

  await page.goto(`/app/projects/${project.id}`);
  await page.getByRole("button", { name: "Interview Stories" }).click();
  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByText(/Mock interview story text/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Save" }).click();
  // Saved story accordion shows "behavioral · Lead Engineer" (question_type · target_role)
  await expect(page.getByText("behavioral · Lead Engineer")).toBeVisible({ timeout: 8_000 });
});
