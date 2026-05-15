import { expect, test } from "../fixtures/api";

test("soft-deletes a page, lists it in trash, and restores it through the API", async ({ api }) => {
  const title = `Trash restore ${crypto.randomUUID()}`;
  const created = await api.post("/api/v1/pages", { data: { title } });
  expect(created.ok()).toBeTruthy();
  const body = (await created.json()) as { object: { id: string } };

  const deleted = await api.delete(`/api/v1/objects/${body.object.id}`);
  expect(deleted.ok()).toBeTruthy();

  const trash = await api.get("/api/v1/objects/trash");
  expect(trash.ok()).toBeTruthy();
  const trashBody = (await trash.json()) as { items: Array<{ id: string; title: string }> };
  expect(trashBody.items).toContainEqual(expect.objectContaining({ id: body.object.id, title }));

  const restored = await api.post(`/api/v1/objects/${body.object.id}/restore`);
  expect(restored.ok()).toBeTruthy();

  const afterRestore = await api.get("/api/v1/objects/trash");
  expect(afterRestore.ok()).toBeTruthy();
  const afterRestoreBody = (await afterRestore.json()) as { items: Array<{ id: string }> };
  expect(afterRestoreBody.items.map((item) => item.id)).not.toContain(body.object.id);
});

