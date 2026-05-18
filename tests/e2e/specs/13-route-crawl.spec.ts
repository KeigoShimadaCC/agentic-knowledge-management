import { expect, test } from "../fixtures/api";

type RouteCase = {
  path: string;
  expectedPath?: string | RegExp;
};

async function expectHealthyDocument(page: import("@playwright/test").Page) {
  await expect(page.locator("body")).toBeVisible();
  await expect.poll(() => page.title()).not.toBe("");
}

async function createPageObject(api: import("@playwright/test").APIRequestContext) {
  const response = await api.post("/api/v1/pages", {
    data: { title: `Route crawl page ${crypto.randomUUID()}` },
  });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { object: { id: string } };
  return body.object.id;
}

async function createSourceObject(api: import("@playwright/test").APIRequestContext) {
  const response = await api.post("/api/v1/sources", {
    data: {
      source_type: "web",
      title: `Route crawl source ${crypto.randomUUID()}`,
      url: "https://example.com/",
    },
  });
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { id: string };
  return body.id;
}

test("crawls app and auth routes without critical console errors", async ({ page, api }) => {
  const pageId = await createPageObject(api);
  const sourceId = await createSourceObject(api);
  const consoleErrors: string[] = [];

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  const routes: RouteCase[] = [
    { path: "/app" },
    { path: "/app/pages" },
    { path: `/app/pages/${pageId}` },
    { path: "/app/assets" },
    { path: "/app/sources" },
    { path: `/app/sources/${sourceId}` },
    { path: "/app/chats" },
    { path: "/app/projects" },
    { path: "/app/inbox" },
    { path: "/app/trash" },
    { path: "/app/settings" },
    { path: "/app/settings/mcp" },
    { path: "/login", expectedPath: /\/app$/ },
    { path: "/register", expectedPath: /\/app$/ },
    { path: "/forgot-password", expectedPath: /\/app$/ },
  ];

  for (const route of routes) {
    await test.step(route.path, async () => {
      consoleErrors.length = 0;
      await page.goto(route.path);
      await expectHealthyDocument(page);

      if (route.expectedPath) {
        await expect(page).toHaveURL(route.expectedPath);
      }

      const critical = consoleErrors.filter((message) => /Uncaught|TypeError/.test(message));
      expect(
        critical,
        `Critical console errors on ${route.path}:\n${consoleErrors.join("\n")}`
      ).toEqual([]);
    });
  }
});
