import { act, renderHook } from "@testing-library/react";
import { hybridSearch, keywordSearch, vectorSearch } from "@/lib/api";
import { useSearch } from "@/lib/hooks/useSearch";

vi.mock("@/lib/api", () => ({
  hybridSearch: vi.fn(),
  keywordSearch: vi.fn(),
  vectorSearch: vi.fn(),
}));

describe("useSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(hybridSearch).mockReset();
    vi.mocked(keywordSearch).mockReset();
    vi.mocked(vectorSearch).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces queries and returns paginated results", async () => {
    const resultItem = {
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
    };
    vi.mocked(hybridSearch).mockResolvedValue({
      results: [resultItem],
      total: 1,
      query: "alp",
      mode: "hybrid",
      embeddings_used: true,
    });

    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.setQuery("a");
      result.current.setQuery("al");
      result.current.setQuery("alp");
    });
    expect(hybridSearch).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(result.current.results).toEqual([resultItem]);
    expect(hybridSearch).toHaveBeenCalledTimes(1);
    expect(hybridSearch).toHaveBeenCalledWith("alp", { limit: 10, debug: false });
    expect(result.current.error).toBeNull();
  });

  it("clears results for short queries", async () => {
    const { result } = renderHook(() => useSearch());

    act(() => result.current.setQuery("a"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });
});
