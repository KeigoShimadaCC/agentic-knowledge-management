import { http, HttpResponse } from "msw";

export const API_BASE = "http://localhost:8000";

const defaultSearchResult = {
  id: "page-1",
  kind: "page" as const,
  title: "Alpha Page",
  snippet: { text: "alpha body", highlights: [] as [number, number][] },
  tags: ["note"],
  score: 0.9,
  keyword_score: 0.7,
  vector_score: 0.1,
  recency_boost: 0.1,
  updated_at: "2026-05-15T00:00:00Z",
  source_type: null,
  ingestion_status: null,
};

export const handlers = [
  http.get(`${API_BASE}/api/v1/auth/me`, () =>
    HttpResponse.json({
      user: {
        id: "user-1",
        email: "test@example.com",
        display_name: "Test User",
        created_at: "2026-05-15T00:00:00Z",
      },
    })
  ),
  http.post(`${API_BASE}/api/v1/search/hybrid`, async ({ request }) => {
    const body = (await request.json()) as { q?: string };
    return HttpResponse.json({
      results: body.q && body.q.length >= 2 ? [defaultSearchResult] : [],
      total: body.q && body.q.length >= 2 ? 1 : 0,
      query: body.q ?? "",
      mode: "hybrid",
      embeddings_used: true,
    });
  }),
  http.get(`${API_BASE}/api/v1/search/keyword`, ({ request }) => {
    const q = new URL(request.url).searchParams.get("q") ?? "";
    return HttpResponse.json({
      results: q.length >= 2 ? [defaultSearchResult] : [],
      total: q.length >= 2 ? 1 : 0,
      query: q,
      mode: "keyword",
    });
  }),
  http.post(`${API_BASE}/api/v1/search/vector`, async ({ request }) => {
    const body = (await request.json()) as { q?: string };
    return HttpResponse.json({
      results: body.q && body.q.length >= 2 ? [defaultSearchResult] : [],
      total: body.q && body.q.length >= 2 ? 1 : 0,
      query: body.q ?? "",
      mode: "semantic",
      embeddings_used: true,
    });
  }),
];
