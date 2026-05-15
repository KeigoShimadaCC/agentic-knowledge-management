import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useAutoSave } from "@/lib/hooks/useAutoSave";
import { API_BASE } from "@/test/msw/handlers";
import { server } from "@/test/msw/server";

describe("useAutoSave", () => {
  it("debounces saves and persists page content once", async () => {
    let patchCalls = 0;
    server.use(
      http.patch(`${API_BASE}/api/v1/pages/page-1`, async () => {
        patchCalls += 1;
        return HttpResponse.json({
          id: "page-1",
          content_json: {},
          content_text: "hello",
          word_count: 1,
          version: 2,
          created_at: "2026-05-15T00:00:00Z",
          updated_at: "2026-05-15T00:00:00Z",
        });
      })
    );

    const { result, rerender } = renderHook(
      ({ contentText }) =>
        useAutoSave("page-1", { content_json: {}, content_text: contentText }, 20),
      { initialProps: { contentText: "hello" } }
    );

    rerender({ contentText: "hello updated" });

    await waitFor(() => expect(patchCalls).toBe(1));
    expect(result.current.status).toBe("saved");
  });

  it("surfaces save errors", async () => {
    server.use(
      http.patch(`${API_BASE}/api/v1/pages/page-1`, () =>
        HttpResponse.json({ detail: "save_failed" }, { status: 500 })
      )
    );

    const { result } = renderHook(() =>
      useAutoSave("page-1", { content_json: {}, content_text: "hello" }, 20)
    );

    await waitFor(() => expect(result.current.status).toBe("error"));
  });
});
