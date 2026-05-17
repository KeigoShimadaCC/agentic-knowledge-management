import { expect, test } from "../fixtures/api";

test("? key opens shortcut overlay", async ({ page }) => {
  await page.goto("/app");
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText(/Keyboard Shortcuts|Global/i).first()).toBeVisible();
});

test("Escape closes shortcut overlay", async ({ page }) => {
  await page.goto("/app");
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
});

test("shortcut overlay lists shortcut rows", async ({ page }) => {
  await page.goto("/app");
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog")).toBeVisible();
  // There should be multiple shortcut descriptions — check at least one known shortcut
  await expect(page.getByText(/Open Search|Cmd\+K|⌘K/i).first()).toBeVisible();
});

test("sidebar collapse via keyboard shortcut (Meta+\\)", async ({ page }) => {
  await page.goto("/app");
  const sidebar = page.locator('[data-tutorial="sidebar"]');
  const before = await sidebar.boundingBox();
  expect(before).not.toBeNull();

  // Dispatch keydown directly to document so the useShortcut handler fires reliably
  await page.evaluate(() => {
    document.dispatchEvent(new KeyboardEvent("keydown", {
      key: "\\",
      code: "Backslash",
      metaKey: true,
      ctrlKey: false,
      bubbles: true,
      cancelable: true,
    }));
  });
  await expect(sidebar).toHaveClass(/w-14/, { timeout: 2_000 });
  await expect.poll(async () => {
    const box = await sidebar.boundingBox();
    return box?.width ?? before!.width;
  }, { timeout: 1_000 }).toBeLessThan(before!.width);

  // Toggle back
  await page.evaluate(() => {
    document.dispatchEvent(new KeyboardEvent("keydown", {
      key: "\\",
      code: "Backslash",
      metaKey: true,
      ctrlKey: false,
      bubbles: true,
      cancelable: true,
    }));
  });
  await expect(sidebar).toHaveClass(/w-60/, { timeout: 2_000 });
});
