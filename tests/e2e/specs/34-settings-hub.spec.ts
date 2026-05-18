import { expect, test } from "../fixtures/api";

test("settings hub renders section tabs", async ({ page }) => {
  await page.goto("/app/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("button", { name: "AI Providers" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Prompts" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Feature Models" })).toBeVisible();
});

test("prompt override save and reset on settings hub", async ({ page }) => {
  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Prompts" }).click();

  const promptCard = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: "Summarize Page", exact: true }) });
  const textarea = promptCard.getByRole("textbox");
  const custom = `E2E custom summary: {content}`;
  await textarea.click();
  await textarea.fill(custom);
  await expect(textarea).toHaveValue(custom);
  await promptCard.getByRole("button", { name: "Save" }).click();
  await expect(promptCard.getByText("Saved")).toBeVisible();

  await expect(promptCard.getByText("Override")).toBeVisible();

  await promptCard.getByRole("button", { name: "Reset" }).click();
  await expect(promptCard.getByText("Override")).toHaveCount(0);
});

test("feature model config saves from settings hub", async ({ page }) => {
  const customModel = `gpt-4o-mini-e2e-${crypto.randomUUID().slice(0, 8)}`;

  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Feature Models" }).click();

  const featureCard = page.locator("article").filter({ hasText: "Summarization" });
  await featureCard.getByPlaceholder("Model").fill(customModel);
  await featureCard.getByRole("button", { name: "Save" }).click();

  await expect(featureCard.getByText(new RegExp(customModel))).toBeVisible();
});

test("MCP connections link opens dedicated MCP settings page", async ({ page }) => {
  await page.goto("/app/settings");
  await page.getByRole("button", { name: "MCP" }).click();
  await page.getByRole("link", { name: "MCP Connections" }).click();
  await expect(page).toHaveURL(/\/app\/settings\/mcp$/);
  await expect(page.getByText(/MCP Connections|MCP Settings/i).first()).toBeVisible();
});
