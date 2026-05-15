import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GraphPanel } from "@/components/graph/GraphPanel";
import { getObjectBacklinks, getObjectRelated } from "@/lib/api";
import { renderWithProviders } from "@/test/render";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getObjectBacklinks: vi.fn(),
    getObjectRelated: vi.fn(),
  };
});

describe("GraphPanel", () => {
  beforeEach(() => {
    vi.mocked(getObjectBacklinks).mockResolvedValue([
      {
        id: "edge-1",
        kind: "links_to",
        weight: 1,
        source_id: "page-2",
        target_id: "page-1",
        source_object: { id: "page-2", kind: "page", title: "Source Page" },
        target_object: { id: "page-1", kind: "page", title: "Target Page" },
        created_at: "2026-05-15T00:00:00Z",
      },
    ]);
    vi.mocked(getObjectRelated).mockResolvedValue([
      {
        id: "source-1",
        kind: "source",
        title: "Related Source",
        distance: 1,
        edge_kind: "cites",
        direction: "outgoing",
      },
    ]);
  });

  it("renders backlinks and switches to related and AI tabs", async () => {
    const user = userEvent.setup();

    renderWithProviders(<GraphPanel objectId="page-1" refreshKey={0} />);

    expect(await screen.findByText("Source Page")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Related" }));
    expect(await screen.findByText("Related Source")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "AI" }));
    expect(screen.getByRole("button", { name: "Summarize" })).toBeInTheDocument();
  });

  it("renders the backlinks empty state", async () => {
    vi.mocked(getObjectBacklinks).mockResolvedValue([]);

    renderWithProviders(<GraphPanel objectId="page-1" refreshKey={0} />);

    await waitFor(() => expect(screen.getByText("No backlinks yet.")).toBeInTheDocument());
  });
});
