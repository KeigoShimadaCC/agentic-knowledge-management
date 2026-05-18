import type { APIRequestContext } from "@playwright/test";

import { expect, test } from "../fixtures/api";
import { createPage } from "../fixtures/pages";
import { importChats } from "../fixtures/scenario-fixtures";

type ObjectOut = {
  id: string;
  title: string;
  description?: string | null;
  tags: string[];
  deleted_at?: string | null;
};

type Paginated<T> = {
  items: T[];
};

type SearchResult = {
  id: string;
  title: string;
};

async function patchPageBody(api: APIRequestContext, pageId: string, text: string) {
  const response = await api.patch(`/api/v1/pages/${pageId}`, {
    data: {
      content_json: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text }] }],
      },
      content_text: text,
    },
  });
  expect(response.ok()).toBeTruthy();
}

test.describe("PHONE-08 cross-platform parity", () => {
  test("Mac-created page is readable, editable, searchable, and restorable through shared APIs", async ({
    page,
    api,
  }) => {
    const marker = crypto.randomUUID();
    const title = `PHONE08 Mac page ${marker}`;
    const objectId = await createPage(api, title, `Mac-originated body ${marker}`);

    const phoneRead = await api.get(`/api/v1/objects/${objectId}`);
    expect(phoneRead.ok()).toBeTruthy();
    await expect(phoneRead.json()).resolves.toMatchObject({ id: objectId, title });

    const phoneEdit = await api.patch(`/api/v1/objects/${objectId}`, {
      data: {
        description: `Edited from phone API ${marker}`,
        tags: ["phone08", "phone-edited"],
      },
    });
    expect(phoneEdit.ok()).toBeTruthy();

    const search = await api.get(`/api/v1/search/keyword?q=${encodeURIComponent(marker)}&limit=10`);
    expect(search.ok()).toBeTruthy();
    const searchBody = (await search.json()) as { results: SearchResult[] };
    expect(searchBody.results.map((result) => result.id)).toContain(objectId);

    await page.goto(`/app/pages/${objectId}`);
    await expect(page.getByText(title)).toBeVisible();
    await expect(page.getByText(`Mac-originated body ${marker}`)).toBeVisible();

    const deleted = await api.delete(`/api/v1/objects/${objectId}`);
    expect(deleted.ok()).toBeTruthy();

    const trash = await api.get("/api/v1/objects/trash");
    expect(trash.ok()).toBeTruthy();
    const trashBody = (await trash.json()) as Paginated<ObjectOut>;
    expect(trashBody.items).toContainEqual(expect.objectContaining({ id: objectId, title }));

    const restored = await api.post(`/api/v1/objects/${objectId}/restore`);
    expect(restored.ok()).toBeTruthy();

    const afterRestore = await api.get(`/api/v1/objects/${objectId}`);
    expect(afterRestore.ok()).toBeTruthy();
    await expect(afterRestore.json()).resolves.toMatchObject({ id: objectId, deleted_at: null });
  });

  test("Phone-originated knowledge renders on Mac and supports graph, project, and workspace propagation", async ({
    page,
    api,
  }) => {
    const marker = crypto.randomUUID();
    const phoneTitle = `PHONE08 iPhone capture ${marker}`;
    const macTitle = `PHONE08 Mac target ${marker}`;

    const phoneCreate = await api.post("/api/v1/pages", {
      data: { title: phoneTitle },
    });
    expect(phoneCreate.ok()).toBeTruthy();
    const phoneBody = (await phoneCreate.json()) as { object: { id: string }; page: { id: string } };
    await patchPageBody(api, phoneBody.page.id, `Phone-originated body ${marker}`);
    const tagPhoneObject = await api.patch(`/api/v1/objects/${phoneBody.object.id}`, {
      data: { tags: ["phone08", "iphone-origin"] },
    });
    expect(tagPhoneObject.ok()).toBeTruthy();

    const macObjectId = await createPage(api, macTitle, `Mac target body ${marker}`);

    await page.goto(`/app/pages/${phoneBody.object.id}`);
    await expect(page.getByText(phoneTitle)).toBeVisible();
    await expect(page.getByText(`Phone-originated body ${marker}`)).toBeVisible();

    const edge = await api.post("/api/v1/edges", {
      data: {
        source_id: phoneBody.object.id,
        target_id: macObjectId,
        kind: "related_to",
      },
    });
    expect(edge.ok()).toBeTruthy();

    const backlinks = await api.get(`/api/v1/objects/${macObjectId}/backlinks`);
    expect(backlinks.ok()).toBeTruthy();
    const backlinkBody = (await backlinks.json()) as Array<{ source: { id: string; title: string } }>;
    expect(backlinkBody).toContainEqual(
      expect.objectContaining({ source: expect.objectContaining({ id: phoneBody.object.id, title: phoneTitle }) })
    );

    const project = await api.post("/api/v1/projects", {
      data: {
        title: `PHONE08 parity project ${marker}`,
        description: "Created by the phone parity test.",
        status: "active",
        tags: ["phone08"],
      },
    });
    expect(project.ok()).toBeTruthy();
    const projectBody = (await project.json()) as { id: string };

    const projectPatch = await api.patch(`/api/v1/projects/${projectBody.id}`, {
      data: { status: "completed", skills: ["swiftui", "nextjs"] },
    });
    expect(projectPatch.ok()).toBeTruthy();
    await expect(projectPatch.json()).resolves.toMatchObject({ status: "completed", skills: ["swiftui", "nextjs"] });

    const workspace = await api.post("/api/v1/workspaces", {
      data: {
        name: `PHONE08 workspace ${marker}`,
        description: "Workspace seeded by cross-platform parity.",
        is_pinned: true,
        layout: {
          version: 1,
          active_pane_id: "main",
          panes: [
            {
              id: "main",
              object_id: phoneBody.object.id,
              object_kind: "page",
              size_pct: 100,
              mode: "read",
            },
          ],
        },
      },
    });
    expect(workspace.ok()).toBeTruthy();
    const workspaceBody = (await workspace.json()) as { id: string };

    const workspacePatch = await api.patch(`/api/v1/workspaces/${workspaceBody.id}`, {
      data: { description: "Updated from the phone parity path.", is_pinned: false },
    });
    expect(workspacePatch.ok()).toBeTruthy();
    await expect(workspacePatch.json()).resolves.toMatchObject({
      id: workspaceBody.id,
      description: "Updated from the phone parity path.",
      is_pinned: false,
    });

    const objectQuery = await api.get(`/api/v1/objects?q=${encodeURIComponent(marker)}&limit=10`);
    expect(objectQuery.ok()).toBeTruthy();
    const objectQueryBody = (await objectQuery.json()) as Paginated<ObjectOut>;
    expect(objectQueryBody.items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: phoneBody.object.id, title: phoneTitle }),
        expect.objectContaining({ id: macObjectId, title: macTitle }),
      ])
    );

    await page.goto(`/app/pages/${macObjectId}`);
    await expect(page.getByText(macTitle)).toBeVisible();
    await expect(page.getByText(`Mac target body ${marker}`)).toBeVisible();
  });

  test("Phone-originated assets, chats, and AI actions propagate to Mac and shared APIs", async ({
    page,
    api,
  }) => {
    const marker = crypto.randomUUID();
    const phoneTitle = `PHONE08 asset chat ${marker}`;
    const csv = `name,value,marker\nAlpha,1,${marker}\n`;

    const upload = await api.post("/api/v1/assets/upload?create_source=true", {
      multipart: {
        file: {
          name: `phone08-${marker}.csv`,
          mimeType: "text/csv",
          buffer: Buffer.from(csv),
        },
      },
    });
    expect(upload.ok()).toBeTruthy();
    const uploadBody = (await upload.json()) as { source: { id: string; title: string } };
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

    const phonePage = await api.post("/api/v1/pages", {
      data: { title: phoneTitle },
    });
    expect(phonePage.ok()).toBeTruthy();
    const phonePageBody = (await phonePage.json()) as {
      object: { id: string };
      page: { id: string };
    };
    await patchPageBody(api, phonePageBody.page.id, `PHONE08 AI body ${marker}`);

    const chatTitle = `PHONE08 chat ${marker}`;
    const [chatId] = await importChats(api, {
      conversations: [
        {
          id: `conv-${marker}`,
          title: chatTitle,
          create_time: 1_700_000_000,
          update_time: 1_700_000_060,
          mapping: {
            "msg-1": {
              id: "msg-1",
              message: {
                id: "msg-1",
                author: { role: "user" },
                create_time: 1_700_000_000,
                content: { content_type: "text", parts: [`PHONE08 chat body ${marker}`] },
                status: "finished_successfully",
                metadata: {},
              },
              parent: null,
              children: [],
            },
          },
        },
      ],
    });
    expect(chatId).toBeTruthy();

    const chatRead = await api.get(`/api/v1/chats/${chatId}`);
    expect(chatRead.ok()).toBeTruthy();
    await expect(chatRead.json()).resolves.toMatchObject({ id: chatId, title: chatTitle });

    const summarize = await api.post("/api/v1/ai/summarize", {
      data: { object_id: phonePageBody.object.id },
    });
    if (summarize.status() === 503) {
      const detail = (await summarize.json()) as { detail?: string };
      expect(detail.detail).toBe("ai_disabled");
    } else {
      expect(summarize.ok()).toBeTruthy();
      const summaryBody = (await summarize.json()) as { summary: string };
      expect(summaryBody.summary.length).toBeGreaterThan(0);
    }

    const answer = await api.post("/api/v1/ai/answer", {
      data: { q: `What is PHONE08 ${marker}?`, object_ids: [phonePageBody.object.id] },
    });
    if (answer.status() === 503) {
      const detail = (await answer.json()) as { detail?: string };
      expect(detail.detail).toBe("ai_disabled");
    } else {
      expect(answer.ok()).toBeTruthy();
      const answerBody = (await answer.json()) as { answer: string };
      expect(answerBody.answer.length).toBeGreaterThan(0);
    }

    const sourceDetail = await api.get(`/api/v1/sources/${sourceId}`);
    expect(sourceDetail.ok()).toBeTruthy();
    const sourceDetailBody = (await sourceDetail.json()) as {
      extracted_text?: string | null;
      preview_data?: { rows?: unknown[] } | null;
    };
    expect(
      sourceDetailBody.extracted_text?.includes(marker) ||
        JSON.stringify(sourceDetailBody.preview_data ?? {}).includes(marker)
    ).toBeTruthy();

    // Mac SSR covers pages/projects (tests 1–2). Source/chat detail routes use client hooks;
    // PHONE-08 propagation for assets and chats is asserted via shared API above.
    const macSourceCheck = await page.goto(`/app/sources/${sourceId}`);
    expect(macSourceCheck?.ok()).toBeTruthy();

    const macChatCheck = await page.goto(`/app/chats/${chatId}`);
    expect(macChatCheck?.ok()).toBeTruthy();
  });
});
