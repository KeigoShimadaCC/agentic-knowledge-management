import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

test("opens a page in a side pane from search result", async ({ page, api }) => {
  const marker = crypto.randomUUID();
  const mainId = await createPage(api, `Pane main ${marker}`, "Main content");
  const sideTitle = `Pane side ${marker}`;
  await createPage(api, sideTitle, "Side content");

  await page.goto(`/app/pages/${mainId}`);
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Search knowledge base...").fill(sideTitle);
  await expect(page.getByText(sideTitle)).toBeVisible({ timeout: 5_000 });
  await page.getByTitle("Open in side pane").click();

  // URL stays on the main page
  await expect(page).toHaveURL(new RegExp(`/app/pages/${mainId}$`));
  // Side pane content is visible (rendered in a react-resizable-panels Panel)
  await expect(page.getByText(sideTitle).last()).toBeVisible({ timeout: 5_000 });
});

test("close pane button removes the side pane", async ({ page, api }) => {
  const marker = crypto.randomUUID();
  const mainId = await createPage(api, `Close pane main ${marker}`, "Main");
  const sideTitle = `Close pane side ${marker}`;
  await createPage(api, sideTitle, "Side");

  await page.goto(`/app/pages/${mainId}`);
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Search knowledge base...").fill(sideTitle);
  await expect(page.getByText(sideTitle)).toBeVisible({ timeout: 5_000 });
  await page.getByTitle("Open in side pane").click();
  await expect(page.getByText(sideTitle).last()).toBeVisible({ timeout: 5_000 });

  await page.getByRole("button", { name: "Close pane" }).click();
  await expect(page.getByRole("button", { name: "Close pane" })).toBeHidden({ timeout: 3_000 });
});

test("save workspace flow: name modal appears, fill, save, modal closes", async ({ page, api }) => {
  const marker = crypto.randomUUID();
  const mainId = await createPage(api, `Save flow main ${marker}`, "Main");
  const sideTitle = `Save flow side ${marker}`;
  await createPage(api, sideTitle, "Side");

  // Mock workspace creation to avoid real DB writes
  await page.route("**/api/v1/workspaces", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        json: {
          id: crypto.randomUUID(),
          name: "My test workspace",
          description: null,
          pane_state: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
        },
      });
    } else {
      await route.fulfill({ json: { items: [], total: 0 } });
    }
  });

  await page.goto(`/app/pages/${mainId}`);
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Search knowledge base...").fill(sideTitle);
  await expect(page.getByText(sideTitle)).toBeVisible({ timeout: 5_000 });
  await page.getByTitle("Open in side pane").click();
  await expect(page.getByText(sideTitle).last()).toBeVisible({ timeout: 5_000 });

  await page.getByRole("button", { name: "Save workspace" }).click();
  await expect(page.getByRole("heading", { name: "Save Workspace" })).toBeVisible({ timeout: 3_000 });

  await page.getByPlaceholder("My research session").fill("My test workspace");
  await page.getByRole("button", { name: "Save", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Save Workspace" })).toBeHidden({ timeout: 5_000 });
});

test("save workspace button is visible when a side pane is open", async ({ page, api }) => {
  const marker = crypto.randomUUID();
  const mainId = await createPage(api, `Workspace main ${marker}`, "Main");
  const sideTitle = `Workspace side ${marker}`;
  await createPage(api, sideTitle, "Side");

  await page.goto(`/app/pages/${mainId}`);
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Search knowledge base...").fill(sideTitle);
  await expect(page.getByText(sideTitle)).toBeVisible({ timeout: 5_000 });
  await page.getByTitle("Open in side pane").click();
  await expect(page.getByText(sideTitle).last()).toBeVisible({ timeout: 5_000 });

  await expect(page.getByRole("button", { name: "Save workspace" })).toBeVisible();
});
