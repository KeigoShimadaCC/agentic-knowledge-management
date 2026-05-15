import { act, renderHook } from "@testing-library/react";
import { updatePage } from "@/lib/api";
import { useAutoSave } from "@/lib/hooks/useAutoSave";

vi.mock("@/lib/api", () => ({
  updatePage: vi.fn(),
}));

describe("useAutoSave", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(updatePage).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("saves once after the idle delay with the latest rapid edit", async () => {
    vi.mocked(updatePage).mockResolvedValue({
      id: "page-1",
      content_json: {},
      content_text: "Second",
      word_count: 1,
      version: 2,
      created_at: "2026-05-15T00:00:00Z",
      updated_at: "2026-05-15T00:00:01Z",
    });

    const { result, rerender } = renderHook(
      ({ text }) => useAutoSave("page-1", { content_text: text }, 800),
      { initialProps: { text: "First" } }
    );

    rerender({ text: "Second" });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(799);
    });
    expect(updatePage).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    expect(result.current.status).toBe("saved");
    expect(updatePage).toHaveBeenCalledTimes(1);
    expect(updatePage).toHaveBeenCalledWith("page-1", { content_text: "Second" });
  });

  it("reports errors when saving fails", async () => {
    vi.mocked(updatePage).mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useAutoSave("page-1", { content_text: "Broken" }, 800));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });

    expect(result.current.status).toBe("error");
  });
});
