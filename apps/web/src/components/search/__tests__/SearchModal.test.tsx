import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchModal } from "@/components/search/SearchModal";
import { useSearch } from "@/lib/hooks/useSearch";
import { renderWithProviders } from "@/test/render";

const push = vi.fn();
const setQuery = vi.fn();
const setMode = vi.fn();
const setDebug = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/hooks/useSearch", () => ({
  useSearch: vi.fn(),
}));

vi.mock("@/components/workspace/ObjectPaneViewer", () => ({
  ObjectPaneViewer: ({ title }: { title: string }) => <div>{title}</div>,
}));

function mockSearch(overrides: Partial<ReturnType<typeof useSearch>> = {}) {
  vi.mocked(useSearch).mockReturnValue({
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
    isLoading: false,
    error: null,
    query: "al",
    setQuery,
    mode: "hybrid",
    setMode,
    debug: false,
    setDebug,
    ...overrides,
  });
}

describe("SearchModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch();
  });

  it("updates query, switches mode, navigates on result selection, and closes on Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    renderWithProviders(<SearchModal isOpen onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: "Keyword" }));
    await user.type(screen.getByPlaceholderText("Search knowledge base..."), "pha");
    await user.click(screen.getByText("Alpha Page"));
    fireEvent.keyDown(document, { key: "Escape" });

    expect(setMode).toHaveBeenCalledWith("keyword");
    expect(setQuery).toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith("/app/pages/page-1");
    expect(onClose).toHaveBeenCalled();
  });

  it("opens a result in the workspace side pane", async () => {
    const user = userEvent.setup();

    renderWithProviders(<SearchModal isOpen onClose={vi.fn()} />);

    await user.click(screen.getByTitle("Open in side pane"));

    expect(screen.getByText("Alpha Page")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
