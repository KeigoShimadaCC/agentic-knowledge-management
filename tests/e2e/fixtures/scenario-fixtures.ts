import { expect, type APIRequestContext } from "@playwright/test";

type SourceType = "web" | "youtube";

type SeedSourcePayload = {
  title: string;
  url: string;
  sourceType: SourceType;
  tags?: string[];
};

type SeedEdgePayload = {
  srcId: string;
  dstId: string;
  relation: string;
};

type ObjectListResponse = {
  items?: Array<{ id: string; tags?: string[] }>;
};

function assertOk(response: { ok(): boolean; status(): number }, bodyText: string, label: string) {
  expect(response.ok(), `${label} failed: ${response.status()} ${bodyText}`).toBeTruthy();
}

export async function seedSource(
  api: APIRequestContext,
  { title, url, sourceType, tags = [] }: SeedSourcePayload
): Promise<string> {
  const response = await api.post("/api/v1/sources", {
    data: {
      title,
      url,
      source_type: sourceType,
      tags,
    },
  });
  const text = await response.text();
  assertOk(response, text, "seedSource");
  return (JSON.parse(text) as { id: string }).id;
}

export async function waitForSource(
  api: APIRequestContext,
  sourceId: string,
  timeoutMs = 60_000
): Promise<void> {
  await expect
    .poll(
      async () => {
        const response = await api.get(`/api/v1/sources/${sourceId}`);
        if (!response.ok()) return "";
        const body = (await response.json()) as { ingestion_status?: string };
        return body.ingestion_status ?? "";
      },
      { timeout: timeoutMs }
    )
    .toBe("ready");
}

export async function seedProject(
  api: APIRequestContext,
  payload: Record<string, unknown>
): Promise<string> {
  const response = await api.post("/api/v1/projects", { data: payload });
  const text = await response.text();
  assertOk(response, text, "seedProject");
  return (JSON.parse(text) as { id: string }).id;
}

export async function seedEdge(api: APIRequestContext, payload: SeedEdgePayload): Promise<void> {
  const response = await api.post("/api/v1/edges", {
    data: {
      source_id: payload.srcId,
      target_id: payload.dstId,
      kind: payload.relation,
    },
  });
  const text = await response.text();
  assertOk(response, text, "seedEdge");
}

export async function importChats(
  api: APIRequestContext,
  jsonContent: unknown
): Promise<string[]> {
  const response = await api.post("/api/v1/chats/import", {
    multipart: {
      file: {
        name: "export.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(jsonContent)),
      },
      provider: "auto",
    },
  });
  const text = await response.text();
  assertOk(response, text, "importChats");
  const body = JSON.parse(text) as { imported: Array<{ id: string }> };
  return body.imported.map((chat) => chat.id);
}

export async function cleanupByTag(api: APIRequestContext, tag: string): Promise<void> {
  while (true) {
    const response = await api.get(`/api/v1/objects?limit=100&tag=${encodeURIComponent(tag)}`);
    const text = await response.text();
    assertOk(response, text, "cleanupByTag list");
    const body = JSON.parse(text) as ObjectListResponse;
    const objects = body.items ?? [];
    if (objects.length === 0) return;

    await Promise.all(objects.map(async (object) => {
      const deleteResponse = await api.delete(`/api/v1/objects/${object.id}`);
      const deleteText = await deleteResponse.text();
      assertOk(deleteResponse, deleteText, `cleanupByTag delete ${object.id}`);
    }));
  }
}
