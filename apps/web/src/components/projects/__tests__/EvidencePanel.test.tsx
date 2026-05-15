import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { createEdge, deleteEdge, getObjectBacklinks, hybridSearch } from "@/lib/api";
import { EvidencePanel } from "@/components/projects/EvidencePanel";

vi.mock("@/lib/api", () => ({
  getObjectBacklinks: vi.fn(),
  deleteEdge: vi.fn(),
  hybridSearch: vi.fn(),
  createEdge: vi.fn(),
}));
vi.mock("@/components/workspace/WorkspaceLiteProvider", () => ({
  useWorkspaceLite: () => ({ openSidePane: vi.fn() }),
}));

describe("EvidencePanel", () => {
  beforeEach(() => {
    vi.mocked(getObjectBacklinks).mockResolvedValue([
      {
        id: "edge-1",
        kind: "belongs_to_project",
        weight: 1,
        source_id: "page-1",
        target_id: "project-1",
        source: { id: "page-1", kind: "page", title: "Page evidence" },
        target: null,
        source_object: { id: "page-1", kind: "page", title: "Page evidence" },
        target_object: null,
        created_at: "2026-05-15T00:00:00Z",
      },
    ]);
  });

  it("groups evidence cards by kind", async () => {
    render(<EvidencePanel projectId="project-1" />);

    expect(await screen.findByText("Pages")).toBeInTheDocument();
    expect(screen.getByText("Page evidence")).toBeInTheDocument();
  });

  it("unlinks evidence", async () => {
    vi.mocked(deleteEdge).mockResolvedValue({} as never);
    render(<EvidencePanel projectId="project-1" />);

    await screen.findByText("Page evidence");
    fireEvent.click(screen.getByRole("button", { name: "Unlink" }));

    await waitFor(() => expect(deleteEdge).toHaveBeenCalledWith("edge-1"));
  });

  it("links selected search result", async () => {
    vi.mocked(hybridSearch).mockResolvedValue({
      results: [
        {
          id: "chat-1",
          kind: "chat",
          title: "Chat evidence",
          snippet: null,
          tags: [],
          score: 1,
          keyword_score: 1,
          vector_score: 0,
          recency_boost: 0,
          updated_at: "2026-05-15T00:00:00Z",
          source_type: null,
          ingestion_status: null,
        },
      ],
      total: 1,
      query: "chat",
      mode: "hybrid",
      embeddings_used: false,
    });
    render(<EvidencePanel projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: /Link evidence/ }));
    fireEvent.change(screen.getByPlaceholderText("Search pages, sources, or chats"), {
      target: { value: "chat" },
    });
    expect(await screen.findByText("Chat evidence")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Chat evidence"));

    await waitFor(() =>
      expect(createEdge).toHaveBeenCalledWith({
        source_id: "chat-1",
        target_id: "project-1",
        kind: "belongs_to_project",
      })
    );
  });
});
