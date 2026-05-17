import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { createTestUser } from "../fixtures/test-user";
import { cleanupByTag } from "../fixtures/scenario-fixtures";

const TAG = `s02-${Date.now().toString(36)}`;
const PROJECT_TITLE = `Freelance Project ${TAG}`;

let projectId = "";
let seedApi: APIRequestContext;

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

async function findProjectId(api: APIRequestContext, title: string): Promise<string> {
  const response = await api.get("/api/v1/projects");
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { items?: Array<{ id: string; title: string }> };
  return body.items?.find((project) => project.title === title)?.id ?? "";
}

async function expectAiPanelOutcome(page: Page) {
  const hasGeneratedContent = (await page.getByText(/\b(led|reduced|improved|built)\b/i).count()) > 0;
  const hasAmberAlert =
    (await page
      .locator('[role="alert"], .border-amber-500\\/40, .bg-amber-500\\/10')
      .count()) > 0;
  expect(hasGeneratedContent || hasAmberAlert).toBeTruthy();
}

test.describe.configure({ mode: "serial", timeout: 90_000 });
test.describe("S02 freelance engineer scenario", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@s02 creates project via UI form", async ({ page }) => {
    await page.goto("/app/projects");
    await page.getByRole("button", { name: "New project" }).click();
    await page.getByLabel("Title").fill(PROJECT_TITLE);
    // Add TAG as a tag via the tags input (last "Type and press Enter" placeholder)
    const tagInputs = page.getByPlaceholder("Type and press Enter");
    await tagInputs.last().fill(TAG);
    await tagInputs.last().press("Enter");
    await page.getByRole("button", { name: "Save" }).click();

    await page.goto("/app/projects");
    await expect(page.getByText(PROJECT_TITLE)).toBeVisible();
    // Use seedApi (no cleanup side-effect) to find the project id
    projectId = await findProjectId(seedApi, PROJECT_TITLE);
    expect(projectId).toBeTruthy();
  });

  test("@s02 project detail renders evidence panel", async ({ page }) => {
    await page.goto(`/app/projects/${projectId}`);
    await expect(page.locator("main").first()).toBeVisible();
    await page.getByRole("button", { name: "Evidence" }).click();
    await expect(page.getByText("Evidence")).toBeVisible();
  });

  test("@s02 resume bullets panel renders", async ({ page }) => {
    await page.goto(`/app/projects/${projectId}`);
    await page.getByRole("button", { name: "Resume Bullets" }).click();
    await expect(page.getByRole("button", { name: "Generate" })).toBeVisible();
    await page.getByRole("button", { name: "Generate" }).click();
    await page.waitForTimeout(3_000);
    await expectAiPanelOutcome(page);
  });

  test("@s02 interview story panel renders", async ({ page }) => {
    await page.goto(`/app/projects/${projectId}`);
    await page.getByRole("button", { name: "Interview Stories" }).click();
    await expect(page.getByRole("button", { name: "Generate" })).toBeVisible();
    await page.getByRole("button", { name: "Generate" }).click();
    await page.waitForTimeout(3_000);
    await expectAiPanelOutcome(page);
  });

  test("@s02 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/projects");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
