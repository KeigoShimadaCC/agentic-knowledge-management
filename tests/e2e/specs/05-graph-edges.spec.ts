import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";

test("links one page to another and shows the backlink", async ({ page, api }) => {
  const marker = crypto.randomUUID();
  const sourceTitle = `Graph source ${marker}`;
  const targetTitle = `Graph target ${marker}`;
  const sourceId = await createPage(api, sourceTitle, `Source page ${marker}`);
  const targetId = await createPage(api, targetTitle, `Target page ${marker}`);

  await page.goto(`/app/pages/${sourceId}`);
  await page.getByTitle("Link to object").click();
  await page.getByPlaceholder("Search objects").fill(targetTitle);
  await page.getByRole("button", { name: new RegExp(`page ${targetTitle}`) }).click();
  await expect(page.getByRole("heading", { name: "Link object" })).toBeVisible();
  const edgeResponsePromise = page.waitForResponse(
    (response) => response.url().includes("/api/v1/edges") && response.status() === 201
  );
  await page.getByRole("button", { name: "Create Link" }).click();
  await edgeResponsePromise;
  await expect
    .poll(async () => {
      const response = await api.get(`/api/v1/objects/${targetId}/backlinks`);
      if (!response.ok()) return 0;
      const backlinks = (await response.json()) as Array<{ source: { id: string } }>;
      return backlinks.filter((edge) => edge.source.id === sourceId).length;
    })
    .toBe(1);

  await page.goto(`/app/pages/${targetId}`);
  await page.getByRole("button", { name: "Backlinks" }).click();
  await expect(page.getByRole("button", { name: new RegExp(`${sourceTitle} page links_to`) })).toBeVisible({
    timeout: 5_000,
  });
});
