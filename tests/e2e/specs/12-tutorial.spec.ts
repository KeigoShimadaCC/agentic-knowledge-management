import { expect, test } from "../fixtures/api";
import { TUTORIAL_STEPS } from "../../../apps/web/src/components/tutorial/tutorial-steps";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Scope Next/Back/Stop clicks to the tutorial popup card to avoid ambiguity
// when the tour navigates to pages that have their own buttons.
const POPUP_SELECTOR = '[data-testid="tutorial-popup"]';

function popupButton(page: import("@playwright/test").Page, name: RegExp) {
  return page.locator(POPUP_SELECTOR).getByRole("button", { name });
}

async function startTour(page: import("@playwright/test").Page) {
  await page.goto("/app");
  const btn = page.getByRole("button", { name: /start tour/i });
  await expect(btn).toBeVisible();
  await btn.click();
  await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });
}

// ---------------------------------------------------------------------------
// API — seed endpoint
// ---------------------------------------------------------------------------

test.describe("Tutorial seed API", () => {
  test("seed creates tutorial objects tagged tutorial_v1", async ({ api }) => {
    const res = await api.post("/api/v1/tutorial/seed");
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as { status: string; seeded: boolean };
    expect(body.status).toBe("ok");
    expect(body.seeded).toBe(true);

    // Verify objects exist with tutorial_v1 tag
    const objects = await api.get("/api/v1/objects?limit=50");
    expect(objects.ok()).toBeTruthy();
    const list = (await objects.json()) as { items: Array<{ tags: string[] }> };
    const tutorialObjects = list.items.filter((o) => o.tags.includes("tutorial_v1"));
    // 3 pages + 1 project = at minimum 4 objects
    expect(tutorialObjects.length).toBeGreaterThanOrEqual(4);
  });

  test("seed is idempotent — second call returns seeded:false", async ({ api }) => {
    const first = await api.post("/api/v1/tutorial/seed");
    expect(first.ok()).toBeTruthy();
    expect(((await first.json()) as { seeded: boolean }).seeded).toBe(true);

    const second = await api.post("/api/v1/tutorial/seed");
    expect(second.ok()).toBeTruthy();
    expect(((await second.json()) as { seeded: boolean }).seeded).toBe(false);
  });

  test("reset soft-deletes tutorial objects", async ({ api }) => {
    // Seed first
    await api.post("/api/v1/tutorial/seed");

    // Reset
    const res = await api.delete("/api/v1/tutorial/reset");
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as { status: string; reset: number };
    expect(body.status).toBe("ok");
    expect(body.reset).toBeGreaterThanOrEqual(4);

    // Objects should no longer appear in the list (soft-deleted)
    const objects = await api.get("/api/v1/objects?limit=50");
    const list = (await objects.json()) as { items: Array<{ tags: string[] }> };
    const tutorialObjects = list.items.filter((o) => o.tags.includes("tutorial_v1"));
    expect(tutorialObjects.length).toBe(0);
  });

  test("reset after reset returns deleted:0", async ({ api }) => {
    await api.post("/api/v1/tutorial/seed");
    await api.delete("/api/v1/tutorial/reset");
    const second = await api.delete("/api/v1/tutorial/reset");
    expect(second.ok()).toBeTruthy();
    expect(((await second.json()) as { reset: number }).reset).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// UI — sidebar button
// ---------------------------------------------------------------------------

test.describe("Tutorial sidebar button", () => {
  test("shows Start Tour in sidebar before tutorial is run", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await expect(page.getByRole("button", { name: /start tour/i })).toBeVisible();
  });

  test("shows Replay Tour after tutorial is completed via localStorage", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.evaluate(() => localStorage.setItem("kos:tutorial:completed", "true"));
    await page.reload();
    await expect(page.getByRole("button", { name: /replay tour/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// UI — tour flow
// ---------------------------------------------------------------------------

test.describe("Tutorial tour UI", () => {
  test("clicking Start Tour shows the welcome step popup", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();

    // Step 1 of N header visible
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });
    // Welcome step title
    await expect(page.getByText(/welcome to knowledgeos/i)).toBeVisible();
  });

  test("Next button advances to step 2", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    await page.getByRole("button", { name: /next/i }).click();
    await expect(page.getByText(/step 2 of/i)).toBeVisible();
  });

  test("Back button returns to previous step", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    // Advance to step 2
    await page.getByRole("button", { name: /next/i }).click();
    await expect(page.getByText(/step 2 of/i)).toBeVisible();

    // Back to step 1 — Back button should now be visible
    await page.getByRole("button", { name: /back/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible();
  });

  test("Stop Tour button dismisses the overlay", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    await page.getByRole("button", { name: /stop tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).not.toBeVisible();
  });

  test("Escape key stops the tour", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    await page.keyboard.press("Escape");
    await expect(page.getByText(/step 1 of/i)).not.toBeVisible();
  });

  test("Back button is hidden on the first step", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    // No Back button on step 1
    await expect(page.getByRole("button", { name: /back/i })).not.toBeVisible();
  });

  test("step with navigateTo navigates the page", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    // Find first step with navigateTo (step 3 = pages)
    const pagesStepIndex = TUTORIAL_STEPS.findIndex((s) => s.navigateTo === "/app/pages");
    expect(pagesStepIndex).toBeGreaterThan(0);

    // Click Next until we hit that step
    for (let i = 0; i < pagesStepIndex; i++) {
      await page.getByRole("button", { name: /next/i }).click();
    }

    // Should have navigated to /app/pages
    await expect(page).toHaveURL(/\/app\/pages/, { timeout: 5_000 });
  });

  test("completing all steps shows Explore button and marks completed in localStorage", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    // Click through all steps — scope Next to the popup card to avoid ambiguity
    const totalSteps = TUTORIAL_STEPS.length;
    for (let i = 0; i < totalSteps - 1; i++) {
      await popupButton(page, /next/i).click();
      await expect(page.getByText(new RegExp(`step ${i + 2} of`, "i"))).toBeVisible({ timeout: 8_000 });
    }

    // Last step should show Explore instead of Next
    await expect(popupButton(page, /explore/i)).toBeVisible();
    await popupButton(page, /explore/i).click();

    // Overlay dismissed
    await expect(page.getByText(new RegExp(`step ${totalSteps} of`))).not.toBeVisible();

    // localStorage flag set
    const completed = await page.evaluate(() => localStorage.getItem("kos:tutorial:completed"));
    expect(completed).toBe("true");
  });

  test("Replay Tour button appears after completion", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    // Simulate prior completion
    await page.evaluate(() => localStorage.setItem("kos:tutorial:completed", "true"));
    await page.reload();
    await expect(page.getByRole("button", { name: /replay tour/i })).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// UI — spotlight / overlay rendering
// ---------------------------------------------------------------------------

test.describe("Tutorial spotlight overlay", () => {
  test("step with a target renders a dark overlay", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    // Step 1 is center (no target). Advance to step 2 which has a sidebar target.
    await page.getByRole("button", { name: /next/i }).click();
    await expect(page.getByText(/step 2 of/i)).toBeVisible();

    // Overlay dark panels should be attached to the DOM (they may have 0 height
    // when the target is near the top of the viewport, so check attachment not visibility)
    const darkPanels = page.locator(".fixed.bg-black\\/70");
    await expect(darkPanels.first()).toBeAttached();
    expect(await darkPanels.count()).toBeGreaterThan(0);
  });

  test("center step (no target) has no dark overlay panels", async ({ page, testUser: _u }) => {
    await page.goto("/app");
    await page.getByRole("button", { name: /start tour/i }).click();

    // Step 1 is welcome — center, no target
    await expect(page.getByText(/step 1 of/i)).toBeVisible({ timeout: 8_000 });

    // No dark overlay panels for center steps
    const darkPanels = page.locator(".fixed.bg-black\\/70");
    await expect(darkPanels).toHaveCount(0);
  });
});
