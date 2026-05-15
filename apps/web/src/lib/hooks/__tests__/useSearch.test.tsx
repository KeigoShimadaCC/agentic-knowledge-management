import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useSearch } from "@/lib/hooks/useSearch";
import { API_BASE } from "@/test/msw/handlers";
import { server } from "@/test/msw/server";

describe("useSearch", () => {
  it("debounces queries and returns paginated results", async () => {
    let searchCalls = 0;
    server.use(
      http.post(`${API_BASE}/api/v1/search/hybrid`, async ({ request }) => {
        searchCalls += 1;
        const body = (await request.json()) as { q?: string };
        return HttpResponse.json({
          results: [
            {
              id: "page-1",
              kind: "page",
              title: "Alpha Note",
              snippet: { text: "alpha body", highlights: [] },
              tags: ["research"],
              score: 0.9,
              keyword_score: 0.7,
              vector_score: 0.1,
              recency_boost: 0.1,
              updated_at: "2026-05-15T00:00:00Z",
              source_type: null,
              ingestion_status: null,
            },
          ],
          total: 1,
          query: body.q ?? "",
          mode: "hybrid",
          embeddings_used: true,
        });
      })
    );

    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.setQuery("a");
      result.current.setQuery("al");
      result.current.setQuery("alp");
    });
    expect(searchCalls).toBe(0);

    await waitFor(() => expect(result.current.results).toHaveLength(1));
    expect(searchCalls).toBe(1);
    expect(result.current.error).toBeNull();
  });

  it("clears results for short queries", async () => {
    const { result } = renderHook(() => useSearch());

    act(() => result.current.setQuery("a"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.results).toEqual([]);
  });
});
