import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { SearchModal } from "@/components/search/SearchModal";
import { API_BASE } from "@/test/msw/handlers";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/render";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/components/workspace/ObjectPaneViewer", () => ({
  ObjectPaneViewer: ({ title }: { title: string }) => <div>{title}</div>,
}));

describe("SearchModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces search input to one hybrid request, navigates on selection, and closes on Escape", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const onClose = vi.fn();
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
              title: "Alpha Page",
              snippet: { text: "alpha body", highlights: [] },
              tags: ["note"],
              score: 0.9,
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

    renderWithProviders(<SearchModal isOpen onClose={onClose} />);

    await user.type(screen.getByPlaceholderText("Search knowledge base..."), "pha");
    await vi.advanceTimersByTimeAsync(300);

    await waitFor(() => expect(searchCalls).toBe(1));
    await user.click(await screen.findByText("Alpha Page"));
    fireEvent.keyDown(document, { key: "Escape" });

    expect(push).toHaveBeenCalledWith("/app/pages/page-1");
    expect(onClose).toHaveBeenCalled();
  });

  it("opens a result in the workspace side pane", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    renderWithProviders(<SearchModal isOpen onClose={vi.fn()} />);

    await user.type(screen.getByPlaceholderText("Search knowledge base..."), "al");
    await vi.advanceTimersByTimeAsync(300);

    await user.click(await screen.findByTitle("Open in side pane"));

    expect(screen.getByText("Alpha Page")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
