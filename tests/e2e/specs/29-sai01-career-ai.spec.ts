import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { test } from "../fixtures/api";
import { cleanupByTag } from "../fixtures/scenario-fixtures";
import { createTestUser } from "../fixtures/test-user";

const TAG = `sai01-${Date.now().toString(36)}`;

let projectId = "";
let seedApi: APIRequestContext;

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

async function openProjectTab(page: Page, tabName: "Resume Bullets" | "Interview Stories") {
  await page.goto(`/app/projects/${projectId}`);
  await page.getByRole("button", { name: tabName }).click();
  await expect(page.getByRole("button", { name: "Generate" })).toBeVisible();
}

test.describe.configure({ mode: "serial", timeout: 60_000 });

test.describe("SAI01 career AI", () => {
  test.beforeAll(async () => {
    const user = await createTestUser();
    seedApi = user.api;
    const res = await seedApi.post("/api/v1/projects", {
      data: {
        title: `E-commerce Rebuild ${TAG}`,
        problem: "Legacy PHP app had 4s average page load and 40% cart abandonment rate",
        actions:
          "Decomposed monolith into 6 FastAPI microservices, migrated frontend to Next.js with Redis caching",
        results: "Reduced page load to 800ms, decreased cart abandonment by 22%, shipped on time",
        role: "Lead Engineer",
        organization: "RetailCo",
      },
    });
    expect(res.ok()).toBeTruthy();
    const project = (await res.json()) as { id: string };
    projectId = project.id;

    const patch = await seedApi.patch(`/api/v1/objects/${projectId}`, { data: { tags: [TAG] } });
    expect(patch.ok()).toBeTruthy();
  });

  test.afterAll(async () => {
    await cleanupByTag(seedApi, TAG);
    await seedApi.dispose();
  });

  test("@sai01 resume bullets generates ≥3 bullets", async ({ page }) => {
    await openProjectTab(page, "Resume Bullets");
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("generate-resume-bullets"),
      { timeout: 20_000 }
    );
    await page.getByRole("button", { name: "Generate" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { bullets: Array<{ text: string }> };
    expect(body.bullets.length).toBeGreaterThanOrEqual(3);
    await expect(page.locator("main").getByText(body.bullets[0].text)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("@sai01 each bullet is substantive", async ({ page }) => {
    await openProjectTab(page, "Resume Bullets");
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("generate-resume-bullets"),
      { timeout: 20_000 }
    );
    await page.getByRole("button", { name: "Generate" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { bullets: Array<{ text: string }> };
    for (const bullet of body.bullets) {
      expect(bullet.text.trim().split(/\s+/).length).toBeGreaterThanOrEqual(8);
    }
  });

  test("@sai01 interview story generates all STAR sections", async ({ page }) => {
    await openProjectTab(page, "Interview Stories");
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("generate-interview-story"),
      { timeout: 20_000 }
    );
    await page.getByRole("button", { name: "Generate" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as {
      story: { situation: string; task: string; action: string; result: string };
    };
    expect(body.story.situation.length).toBeGreaterThan(20);
    expect(body.story.task.length).toBeGreaterThan(20);
    expect(body.story.action.length).toBeGreaterThan(20);
    expect(body.story.result.length).toBeGreaterThan(20);
  });

  test("@sai01 interview story renders in UI", async ({ page }) => {
    await openProjectTab(page, "Interview Stories");
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes("generate-interview-story"),
      { timeout: 20_000 }
    );
    await page.getByRole("button", { name: "Generate" }).click();
    await responsePromise;
    await expect(page.locator("main").getByText(/situation|task|action|result/i).first()).toBeVisible({
      timeout: 5_000,
    });
  });

  test("@sai01 no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/app/projects");
    await expect(page.locator("body")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
