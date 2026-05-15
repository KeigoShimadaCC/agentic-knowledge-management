import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

test("opens a search result in the side pane without navigating away", async ({ page, api }) => {
  const marker = crypto.randomUUID();
  const mainId = await createPage(api, `Workspace main ${marker}`, `Main content ${marker}`);
  const sideTitle = `Workspace side ${marker}`;
  await createPage(api, sideTitle, `Side pane content ${marker}`);

  await page.goto(`/app/pages/${mainId}`);
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Search knowledge base...").fill(sideTitle);
  await expect(page.getByText(sideTitle)).toBeVisible({ timeout: 5_000 });
  await page.getByTitle("Open in side pane").click();

  await expect(page).toHaveURL(new RegExp(`/app/pages/${mainId}$`));
  await expect(page.locator("aside").getByText(sideTitle)).toBeVisible();
  await expect(page.locator("aside").getByText(`Side pane content ${marker}`)).toBeVisible();
});

