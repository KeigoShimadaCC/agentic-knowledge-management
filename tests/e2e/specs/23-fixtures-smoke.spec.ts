import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "../fixtures/api";
import {
  cleanupByTag,
  importChats,
  seedProject,
  seedSource,
  waitForSource,
} from "../fixtures/scenario-fixtures";

const TAG = `smoke-${Date.now()}`;
const chatExportPath = path.join(
  process.cwd(),
  "fixtures/seed-data/chats/synthetic-chatgpt.json"
);
const projectPath = path.join(process.cwd(), "fixtures/seed-data/projects/freelance-project.json");
const chatExport = JSON.parse(readFileSync(chatExportPath, "utf-8")) as {
  conversations: unknown[];
};
const projectPayload = JSON.parse(readFileSync(projectPath, "utf-8")) as Record<string, unknown>;

test.describe("fixtures-smoke", () => {
  test("seedSource creates a tagged web source", async ({ api }) => {
    const sourceId = await seedSource(api, {
      title: "Wikipedia Knowledge Management",
      url: "https://en.wikipedia.org/wiki/Knowledge_management",
      sourceType: "web",
      tags: [TAG],
    });

    const response = await api.get(`/api/v1/sources/${sourceId}`);
    expect(response.ok()).toBeTruthy();
    const body = (await response.json()) as { title: string; source_type: string; tags: string[] };
    expect(body.title).toBe("Wikipedia Knowledge Management");
    expect(body.source_type).toBe("web");
    expect(body.tags).toContain(TAG);
  });

  test("waitForSource polls until source ingestion is ready", async ({ api }) => {
    const sourceId = await seedSource(api, {
      title: "Wikipedia Machine Learning",
      url: "https://en.wikipedia.org/wiki/Machine_learning",
      sourceType: "web",
      tags: [TAG],
    });

    await waitForSource(api, sourceId);
  });

  test("seedProject creates a project", async ({ api }) => {
    const projectId = await seedProject(api, { ...projectPayload, tags: [TAG] });

    const response = await api.get(`/api/v1/projects/${projectId}`);
    expect(response.ok()).toBeTruthy();
    const body = (await response.json()) as { title: string; tags: string[] };
    expect(body.title).toBe("E-commerce Platform Rebuild");
    expect(body.tags).toContain(TAG);
  });

  test("importChats imports the first five conversations", async ({ api }) => {
    const ids = await importChats(api, { conversations: chatExport.conversations.slice(0, 5) });

    expect(ids).toHaveLength(5);
  });

  test("cleanupByTag soft-deletes all tagged objects", async ({ api }) => {
    await seedSource(api, {
      title: "Cleanup Tagged Knowledge Management",
      url: "https://en.wikipedia.org/wiki/Knowledge_management",
      sourceType: "web",
      tags: [TAG],
    });
    await seedProject(api, { ...projectPayload, title: "Cleanup Tagged Project", tags: [TAG] });

    await cleanupByTag(api, TAG);

    const response = await api.get(`/api/v1/objects?limit=100&tag=${encodeURIComponent(TAG)}`);
    expect(response.ok()).toBeTruthy();
    const body = (await response.json()) as { items: unknown[] };
    expect(body.items).toHaveLength(0);
  });
});
