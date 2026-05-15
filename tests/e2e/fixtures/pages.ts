import { expect, type APIRequestContext } from "@playwright/test";

export async function createPage(
  api: APIRequestContext,
  title: string,
  contentText = title
): Promise<string> {
  const response = await api.post("/api/v1/pages", { data: { title } });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { object: { id: string }; page: { id: string } };

  const patch = await api.patch(`/api/v1/pages/${body.page.id}`, {
    data: {
      content_json: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text: contentText }] }],
      },
      content_text: contentText,
    },
  });
  expect(patch.ok()).toBeTruthy();

  return body.object.id;
}

