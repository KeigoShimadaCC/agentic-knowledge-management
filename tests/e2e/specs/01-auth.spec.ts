import { expect, test } from "@playwright/test";

const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8001";

test("registers, logs out, logs in, and resolves auth/me", async ({ page }) => {
  const email = `auth-${crypto.randomUUID()}@example.com`;
  const password = "auth-password";

  await page.goto("/register");
  await page.getByRole("textbox").nth(0).fill("Auth User");
  await page.getByRole("textbox").nth(1).fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByText("Auth User")).toBeVisible();

  const cookies = await page.context().cookies();
  const session = cookies.find((cookie) => cookie.name === "kos_session");
  expect(session?.value).toBeTruthy();
  const me = await page.request.get(`${apiURL}/api/v1/auth/me`, {
    headers: { Cookie: `kos_session=${session?.value}` },
  });
  expect(me.ok()).toBeTruthy();
  const meBody = (await me.json()) as { user: { email: string } };
  expect(meBody.user.email).toBe(email);

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/app$/);
  const loginSession = (await page.context().cookies()).find((cookie) => cookie.name === "kos_session");
  expect(loginSession?.value).toBeTruthy();
  const loginMe = await page.request.get(`${apiURL}/api/v1/auth/me`, {
    headers: { Cookie: `kos_session=${loginSession?.value}` },
  });
  expect(loginMe.ok()).toBeTruthy();
});
