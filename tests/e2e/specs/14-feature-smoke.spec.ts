import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

const hasV2Editor = process.env.NEXT_PUBLIC_UX_EDITOR_V2 === "1";

async function openPageDetail(
  page: import("@playwright/test").Page,
  api: import("@playwright/test").APIRequestContext,
  title: string
) {
  const objectId = await createPage(api, title, `${title} body`);
  await page.goto(`/app/pages/${objectId}`);
  await expect(page.locator(".ProseMirror")).toBeVisible();
  return objectId;
}

test("slash menu renders", async ({ page, api }) => {
  test.skip(!hasV2Editor, "Slash menu is only mounted when NEXT_PUBLIC_UX_EDITOR_V2=1.");

  await openPageDetail(page, api, `Slash smoke ${crypto.randomUUID()}`);
  const editor = page.locator(".ProseMirror");
  await editor.click();
  await page.keyboard.type("/");

  await expect(page.getByRole("button", { name: /Heading 1|Paragraph/ }).first()).toBeVisible();
});

test("bubble menu renders", async ({ page, api }) => {
  test.skip(!hasV2Editor, "Bubble menu is only mounted when NEXT_PUBLIC_UX_EDITOR_V2=1.");

  await openPageDetail(page, api, `Bubble smoke ${crypto.randomUUID()}`);
  const editor = page.locator(".ProseMirror");
  await editor.click();
  await page.keyboard.type("Bubble menu selected text");
  await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");

  await expect(page.getByRole("button", { name: /Bold/ })).toBeVisible();
});

test("AI panel tabs are visible", async ({ page, api }) => {
  await openPageDetail(page, api, `AI panel smoke ${crypto.randomUUID()}`);

  await expect(page.getByTestId("graph-tab-backlinks")).toHaveText("Backlinks");
  await expect(page.getByTestId("graph-tab-related")).toHaveText("Related");
  await expect(page.getByTestId("graph-tab-ai")).toHaveText("AI");

  await page.getByTestId("graph-tab-ai").click();
  await expect(page.getByText("Summarize").first()).toBeVisible();
});

test("shortcut overlay renders", async ({ page }) => {
  await page.goto("/app");
  await page.keyboard.press("?");

  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText(/Keyboard Shortcuts|Global/).first()).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
});

test("bulk action bar renders after selecting a page", async ({ page, api }) => {
  const pageTitle = `Bulk smoke ${crypto.randomUUID()}`;
  await createPage(api, pageTitle, `${pageTitle} body`);
  await page.goto("/app/pages");

  const checkbox = page.getByRole("checkbox", { name: new RegExp(`Select ${pageTitle}`) });
  await expect(checkbox).toBeVisible();
  await checkbox.check();

  await expect(page.getByText(/\d+ selected/)).toBeVisible();
});

test("search filters render", async ({ page }) => {
  await page.goto("/app");
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");

  await expect(page.getByRole("button", { name: "Keyword" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Semantic" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Hybrid" })).toBeVisible();
});

test("sidebar collapse narrows the sidebar", async ({ page }) => {
  await page.goto("/app");

  const sidebar = page.locator('[data-tutorial="sidebar"]');
  await expect(sidebar).toBeVisible();
  const before = await sidebar.boundingBox();
  expect(before).not.toBeNull();

  await page.getByRole("button", { name: /collapse sidebar/i }).click();
  await expect(page.getByRole("button", { name: /expand sidebar/i })).toBeVisible();
  // Wait for the CSS transition (transition-all duration-base = 180ms) to complete
  await expect(sidebar).toHaveClass(/w-14/, { timeout: 2_000 });
  await expect.poll(async () => {
    const box = await sidebar.boundingBox();
    return box?.width ?? before!.width;
  }, { timeout: 1_000 }).toBeLessThan(before!.width);
});
