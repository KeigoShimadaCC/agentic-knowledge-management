import { expect, test } from "@playwright/test";

const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8001";

test("/ redirects directly to /app — no login gate", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/app/);
  // sidebar landmark proves the app shell rendered
  await expect(page.locator("aside")).toBeVisible();
});

test("/login redirects to /app", async ({ page }) => {
  await page.goto("/login");
  await expect(page).toHaveURL(/\/app/);
});

test("/register redirects to /app", async ({ page }) => {
  await page.goto("/register");
  await expect(page).toHaveURL(/\/app/);
});

test("/forgot-password redirects to /app", async ({ page }) => {
  await page.goto("/forgot-password");
  await expect(page).toHaveURL(/\/app/);
});

test("/auth/me returns the local user without any cookie", async ({ request }) => {
  const res = await request.get(`${apiURL}/api/v1/auth/me`);
  expect(res.ok()).toBeTruthy();
  const body = (await res.json()) as { user: { id: string; email: string } };
  expect(body.user.id).toBeTruthy();
  expect(body.user.email).toBeTruthy();
});

test("sidebar has no sign-out button", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator("aside")).toBeVisible();
  await expect(page.getByRole("button", { name: /sign out/i })).not.toBeVisible();
});
