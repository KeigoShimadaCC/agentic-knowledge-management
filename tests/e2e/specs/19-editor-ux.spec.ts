import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

const hasV2Editor = process.env.NEXT_PUBLIC_UX_EDITOR_V2 === "1";

async function openEditor(
  page: import("@playwright/test").Page,
  api: import("@playwright/test").APIRequestContext,
  title: string
) {
  const id = await createPage(api, title, `${title} body`);
  await page.goto(`/app/pages/${id}`);
  await expect(page.locator(".ProseMirror")).toBeVisible();
  return id;
}

test("editor toolbar renders Bold button", async ({ page, api }) => {
  await openEditor(page, api, `Toolbar test ${crypto.randomUUID()}`);
  await expect(page.getByTitle("Bold")).toBeVisible();
});

test("editor toolbar renders Italic button", async ({ page, api }) => {
  await openEditor(page, api, `Toolbar italic ${crypto.randomUUID()}`);
  await expect(page.getByTitle("Italic")).toBeVisible();
});

test("editor toolbar renders Heading 1 button", async ({ page, api }) => {
  await openEditor(page, api, `Toolbar h1 ${crypto.randomUUID()}`);
  await expect(page.getByTitle("Heading 1")).toBeVisible();
});

test("slash menu renders (V2 editor)", async ({ page, api }) => {
  test.skip(!hasV2Editor, "Slash menu requires NEXT_PUBLIC_UX_EDITOR_V2=1");
  await openEditor(page, api, `Slash V2 ${crypto.randomUUID()}`);
  const editor = page.locator(".ProseMirror");
  await editor.click();
  await page.keyboard.type("/");
  await expect(page.getByRole("button", { name: /Heading 1|Paragraph/ }).first()).toBeVisible();
});

test("bubble menu renders on text selection (V2 editor)", async ({ page, api }) => {
  test.skip(!hasV2Editor, "Bubble menu requires NEXT_PUBLIC_UX_EDITOR_V2=1");
  await openEditor(page, api, `Bubble V2 ${crypto.randomUUID()}`);
  const editor = page.locator(".ProseMirror");
  await editor.click();
  await page.keyboard.type("Select this text for bubble menu.");
  await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await expect(page.getByRole("button", { name: /Bold/ })).toBeVisible({ timeout: 3_000 });
});
