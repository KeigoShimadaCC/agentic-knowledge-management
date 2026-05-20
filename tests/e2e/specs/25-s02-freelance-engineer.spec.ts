import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { addUserCookie, createTestUser } from "../fixtures/test-user";
import { cleanupByTag } from "../fixtures/scenario-fixtures";

const TAG = `s02-${Date.now().toString(36)}`;
const PROJECT_TITLE = `Freelance Project ${TAG}`;

let projectId = "";
let seedApi: APIRequestContext;
let savedCookie = "";

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

async function expectAiContent(page: Page, generateUrlFragment: string) {
  // Wait for the actual AI response to land, then assert real content appeared.
  // If the API returns 503 (no key / model disabled), the amber alert is shown — accept that.
  const responsePromise = page.waitForResponse(
    (r) => r.url().includes(generateUrlFragment),
    { timeout: 20_000 }
  );
  await page.getByRole("button", { name: "Generate" }).click();
  const response = await responsePromise;

  if (response.status() === 503) {
    // Graceful AI-disabled path — amber alert must be visible
    await expect(
      page.locator('[role="alert"], .border-amber-500\\/40, .bg-amber-500\\/10').first()
    ).toBeVisible({ timeout: 5_000 });
    return;
  }

  expect(response.ok()).toBeTruthy();
  // Content must appear in the UI — at least one non-trivial word from typical AI output
  await expect(page.getByText(/\b(led|reduced|improved|built|situation|task|action|result)\b/i).first()).toBeVisible({
    timeout: 5_000,
  });
}

test.describe.configure({ mode: "serial", timeout: 120_000 });
test.describe("S02 freelance engineer scenario", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    savedCookie = user.cookie;
  });

  test.beforeEach(async ({ context }) => {
    // Scenario specs run their own login in beforeAll (separate from the `api`
    // fixture). The browser context needs the same session cookie so its
    // requests resolve to the demo user; otherwise they fall through to the
    // desktop-profile single-user fallback and see a different user.
    await addUserCookie(context, savedCookie);
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@s02 creates project via UI form", async ({ page }) => {
    await page.goto("/app/projects");
    await page.getByRole("button", { name: "New project" }).click();
    await page.getByLabel("Title").fill(PROJECT_TITLE);
    const tagInputs = page.getByPlaceholder("Type and press Enter");
    await tagInputs.last().fill(TAG);
    await tagInputs.last().press("Enter");
    await page.getByRole("button", { name: "Save" }).click();

    await page.goto("/app/projects");
    await expect(page.getByText(PROJECT_TITLE)).toBeVisible();

    projectId = await findProjectId(seedApi, PROJECT_TITLE);
    expect(projectId).toBeTruthy();

    // Patch with rich content so AI generators have something to work with
    const patch = await seedApi.patch(`/api/v1/projects/${projectId}`, {
      data: {
        role: "Lead Engineer",
        organization: "RetailCo",
        description: "Led full rebuild of legacy PHP monolith into React + FastAPI microservices",
        problem: "Legacy PHP app had 4s average page load and 40% cart abandonment rate",
        actions: "Decomposed monolith into 6 FastAPI services, migrated frontend to Next.js, added Redis caching",
        results: "Reduced page load to 800ms, decreased cart abandonment by 22%",
      },
    });
    expect(patch.ok()).toBeTruthy();
  });

  test("@s02 project detail renders evidence panel", async ({ page }) => {
    await page.goto(`/app/projects/${projectId}`);
    await expect(page.locator("main").first()).toBeVisible();
    await page.getByRole("button", { name: "Evidence" }).click();
    await expect(page.getByText("Evidence")).toBeVisible();
  });

  test("@s02 resume bullets panel renders and generates content", async ({ page }) => {
    await page.goto(`/app/projects/${projectId}`);
    await page.getByRole("button", { name: "Resume Bullets" }).click();
    await expect(page.getByRole("button", { name: "Generate" })).toBeVisible();
    await expectAiContent(page, "generate-resume-bullets");
  });

  test("@s02 interview story panel renders and generates content", async ({ page }) => {
    await page.goto(`/app/projects/${projectId}`);
    await page.getByRole("button", { name: "Interview Stories" }).click();
    await expect(page.getByRole("button", { name: "Generate" })).toBeVisible();
    await expectAiContent(page, "generate-interview-story");
  });

  test("@s02 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/projects");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
