import { expect, test } from "../fixtures/api";

test("uploads a CSV source and renders extracted preview rows", async ({ page, api }) => {
  const marker = `csv-${crypto.randomUUID()}`;
  const csv = `name,value,marker\nAlpha,1,${marker}\nBeta,2,${marker}\n`;

  await page.goto("/app/sources");
  await page.getByRole("button", { name: "Create source" }).click();
  await page.getByRole("button", { name: "Upload File" }).click();
  const uploadResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/assets/upload?create_source=true") && response.status() === 201
  );
  await page.locator('input[type="file"]').setInputFiles({
    name: `${marker}.csv`,
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  const uploadResponse = await uploadResponsePromise;
  const uploadBody = (await uploadResponse.json()) as { source: { id: string } };
  const sourceId = uploadBody.source.id;

  await expect
    .poll(
      async () => {
        const response = await api.get(`/api/v1/sources/${sourceId}`);
        if (!response.ok()) return "";
        const source = (await response.json()) as { ingestion_status: string };
        return source.ingestion_status;
      },
      { timeout: 30_000 }
    )
    .toBe("ready");

  await page.goto(`/app/sources/${sourceId}`);
  await expect(page.getByRole("heading", { name: "CSV Preview" })).toBeVisible();
  await expect(page.getByText("Alpha")).toBeVisible();
  await expect(page.getByText(marker).first()).toBeVisible();
});
