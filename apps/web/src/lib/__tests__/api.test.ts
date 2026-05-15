import { http, HttpResponse } from "msw";
import {
  aiAnswer,
  aiExtractClaims,
  aiExtractTasks,
  aiSuggestLinks,
  aiSummarize,
  aiTriage,
  apiFetch,
  applyStructuredChatSummary,
  createEdge,
  createPage,
  createSource,
  deleteSource,
  generateStructuredChatSummary,
  getChat,
  getInbox,
  getMe,
  getObjectBacklinks,
  getObjectRelated,
  getPage,
  getRawChatUrl,
  getSource,
  getStructuredChatSummary,
  hybridSearch,
  importChatContent,
  importChatFile,
  keywordSearch,
  listChats,
  listEdges,
  listObjects,
  listSources,
  listTrashObjects,
  login,
  logout,
  register,
  restoreObject,
  updateObject,
  updatePage,
  uploadAsset,
  vectorSearch,
} from "@/lib/api";
import { ApiError } from "@/types";
import { server } from "@/test/msw/server";

const API_BASE = "http://localhost:8000";

describe("apiFetch", () => {
  it("includes credentials and JSON headers", async () => {
    let sawCookieCredentials = false;
    let sawJsonHeader = false;

    server.use(
      http.post(`${API_BASE}/api/v1/example`, ({ request }) => {
        sawCookieCredentials = request.credentials === "include";
        sawJsonHeader = request.headers.get("content-type") === "application/json";
        return HttpResponse.json({ ok: true });
      })
    );

    await expect(apiFetch<{ ok: boolean }>("/api/v1/example", { method: "POST" })).resolves.toEqual({
      ok: true,
    });
    expect(sawCookieCredentials).toBe(true);
    expect(sawJsonHeader).toBe(true);
  });

  it("maps string detail errors to ApiError", async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/fail`, () =>
        HttpResponse.json({ detail: "not allowed" }, { status: 403 })
      )
    );

    await expect(apiFetch("/api/v1/fail")).rejects.toMatchObject({
      status: 403,
      message: "not allowed",
    } satisfies Partial<ApiError>);
  });

  it("maps validation detail arrays into readable messages", async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/invalid`, () =>
        HttpResponse.json(
          { detail: [{ loc: ["body", "title"], msg: "Field required" }] },
          { status: 422 }
        )
      )
    );

    await expect(apiFetch("/api/v1/invalid")).rejects.toMatchObject({
      status: 422,
      message: "body.title: Field required",
    } satisfies Partial<ApiError>);
  });

  it("routes exported API helpers to the expected HTTP methods and paths", async () => {
    const calls: Array<{ method: string; path: string; body: unknown }> = [];

    server.use(
      http.all(`${API_BASE}/*`, async ({ request }) => {
        const url = new URL(request.url);
        const contentType = request.headers.get("content-type") ?? "";
        const bodyText = await request.text();
        calls.push({
          method: request.method,
          path: `${url.pathname}${url.search}`,
          body: contentType.includes("application/json") && bodyText ? JSON.parse(bodyText) : null,
        });
        return HttpResponse.json({ ok: true, results: [], items: [] });
      })
    );

    const file = new File(["x"], "test.txt", { type: "text/plain" });

    await getMe();
    await login("a@example.com", "secret");
    await register("a@example.com", "secret", "A");
    await logout();
    await listObjects({ kind: "page", q: "alpha", page: 2, limit: 5 });
    await listTrashObjects();
    await restoreObject("object-1");
    await createPage("New Page");
    await getPage("page-1");
    await updatePage("page-1", { title: "Updated" });
    await uploadAsset(file);
    await listSources({ source_type: "pdf", ingestion_status: "ready", q: "paper" });
    await createSource({ source_type: "web", url: "https://example.com", title: "Example" });
    await getSource("source-1");
    await deleteSource("source-1");
    await listChats({ provider: "claude", q: "thread" });
    await getChat("chat-1");
    await importChatContent({ content: "hi", provider: "plain_text", raw_format: "txt" });
    await importChatFile({ file, provider: "plain_text", title: "Upload" });
    await generateStructuredChatSummary("chat-1");
    await getStructuredChatSummary("chat-1");
    await applyStructuredChatSummary("chat-1");
    await createEdge({ source_id: "a", target_id: "b", kind: "links_to" });
    await listEdges({ source_id: "a", kind: "links_to" });
    await keywordSearch("alpha", { kind: "page", limit: 3 });
    await vectorSearch("alpha", { kind: "page", limit: 3 });
    await hybridSearch("alpha", { kind: "page", limit: 3, debug: true });
    await getObjectBacklinks("object-1");
    await getObjectRelated("object-1", 2);
    await aiSummarize("object-1", true);
    await aiExtractClaims("object-1");
    await aiExtractTasks("object-1");
    await aiSuggestLinks("object-1", 4);
    await aiAnswer("question", "page");
    await aiTriage("object-1");
    await getInbox({ limit: 10, offset: 20 });
    await updateObject("object-1", { title: "Updated", tags: ["tag"] });

    expect(getRawChatUrl("chat-1")).toBe(`${API_BASE}/api/v1/chats/chat-1/raw`);
    expect(calls.map((call) => `${call.method} ${call.path}`)).toEqual([
      "GET /api/v1/auth/me",
      "POST /api/v1/auth/login",
      "POST /api/v1/auth/register",
      "POST /api/v1/auth/logout",
      "GET /api/v1/objects?kind=page&q=alpha&page=2&limit=5",
      "GET /api/v1/objects/trash",
      "POST /api/v1/objects/object-1/restore",
      "POST /api/v1/pages",
      "GET /api/v1/pages/page-1",
      "PATCH /api/v1/pages/page-1",
      "POST /api/v1/assets/upload",
      "GET /api/v1/sources?source_type=pdf&ingestion_status=ready&q=paper",
      "POST /api/v1/sources",
      "GET /api/v1/sources/source-1",
      "DELETE /api/v1/sources/source-1",
      "GET /api/v1/chats?provider=claude&q=thread",
      "GET /api/v1/chats/chat-1",
      "POST /api/v1/chats/import",
      "POST /api/v1/chats/import",
      "POST /api/v1/chats/chat-1/structured-summary",
      "GET /api/v1/chats/chat-1/structured-summary",
      "POST /api/v1/chats/chat-1/structured-summary/apply",
      "POST /api/v1/edges",
      "GET /api/v1/edges?source_id=a&kind=links_to",
      "GET /api/v1/search/keyword?q=alpha&kind=page&limit=3",
      "POST /api/v1/search/vector",
      "POST /api/v1/search/hybrid",
      "GET /api/v1/objects/object-1/backlinks",
      "GET /api/v1/objects/object-1/related?depth=2&limit=15",
      "POST /api/v1/ai/summarize",
      "POST /api/v1/ai/extract-claims",
      "POST /api/v1/ai/extract-tasks",
      "POST /api/v1/ai/suggest-links",
      "POST /api/v1/ai/answer",
      "POST /api/v1/ai/triage",
      "GET /api/v1/ai/inbox?limit=10&offset=20",
      "PATCH /api/v1/objects/object-1",
    ]);
    expect(calls.find((call) => call.path === "/api/v1/search/hybrid")?.body).toMatchObject({
      q: "alpha",
      kind: "page",
      limit: 3,
      debug: true,
    });
  });
});
