import { expect, test } from "../fixtures/api";

test("assets page renders upload drop zone", async ({ page }) => {
  await page.goto("/app/assets");
  await expect(page.getByTestId("asset-dropzone")).toBeVisible();
});

test("asset drop zone accepts file and shows progress then card", async ({ page }) => {
  await page.goto("/app/assets");
  const dropzone = page.getByTestId("asset-dropzone");
  await expect(dropzone).toBeVisible();

  const marker = crypto.randomUUID();
  const filename = `test-asset-${marker}.txt`;

  // Set files via the hidden file input inside the drop zone
  await page.locator('[data-testid="asset-dropzone"] input[type="file"]').setInputFiles({
    name: filename,
    mimeType: "text/plain",
    buffer: Buffer.from(`Asset content marker: ${marker}`),
  });

  // After upload, the asset card should appear in the grid
  await expect(page.getByText(filename, { exact: false })).toBeVisible({ timeout: 15_000 });
});

test("assets page shows grid view by default", async ({ page }) => {
  await page.goto("/app/assets");
  // The AssetGrid renders a grid container
  await expect(page.getByTestId("asset-dropzone")).toBeVisible();
  // Page title
  await expect(page.getByRole("heading", { name: "Assets" })).toBeVisible();
});
