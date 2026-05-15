import { expect, test } from "../fixtures/api";

test("searches created pages with Cmd+K and opens a result", async ({ page, api }) => {
  const keyword = `needle-${crypto.randomUUID()}`;
  const titles = [`Alpha ${keyword}`, `Beta ${keyword}`, `Gamma ${keyword}`];
  const createdIds: string[] = [];

  for (const title of titles) {
    const response = await api.post("/api/v1/pages", { data: { title } });
    expect(response.ok()).toBeTruthy();
    const body = (await response.json()) as { object: { id: string }; page: { id: string } };
    createdIds.push(body.object.id);
    await api.patch(`/api/v1/pages/${body.page.id}`, {
      data: {
        content_json: { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: keyword }] }] },
        content_text: keyword,
      },
    });
  }

  await page.goto("/app");
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Search knowledge base...").fill(keyword);

  await expect(page.getByText(titles[0])).toBeVisible({ timeout: 5_000 });
  await page.getByRole("button", { name: new RegExp(`page ${titles[0]}`) }).click();

  await expect(page).toHaveURL(new RegExp(`/app/pages/${createdIds[0]}$`));
});
