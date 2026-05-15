import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TriageModal } from "@/components/inbox/TriageModal";
import { aiTriage, updateObject } from "@/lib/api";
import { renderWithProviders } from "@/test/render";
import type { ObjectOut } from "@/types";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    aiTriage: vi.fn(),
    updateObject: vi.fn(),
    createEdge: vi.fn(),
  };
});

const object: ObjectOut = {
  id: "object-1",
  user_id: "user-1",
  kind: "page",
  title: "Untitled Page",
  description: null,
  tags: [],
  metadata: {},
  is_pinned: false,
  is_archived: false,
  ai_generated: false,
  created_at: "2026-05-15T00:00:00Z",
  updated_at: "2026-05-15T00:00:00Z",
  deleted_at: null,
};

describe("TriageModal", () => {
  it("toggles suggested tags, edits the title, and applies one object patch", async () => {
    const user = userEvent.setup();
    const onApplied = vi.fn();
    const onClose = vi.fn();
    vi.mocked(aiTriage).mockResolvedValue({
      suggested_tags: ["research", "draft"],
      suggested_title: "Organized Page",
      summary: "Useful summary",
      agent_run_id: "run-1",
    });
    vi.mocked(updateObject).mockResolvedValue({ ...object, title: "Organized Final" });

    renderWithProviders(
      <TriageModal object={object} onApplied={onApplied} onClose={onClose} />,
      { withWorkspace: false }
    );

    await user.click(screen.getByRole("button", { name: "Analyze with AI" }));
    const titleInput = await screen.findByDisplayValue("Organized Page");
    await user.clear(titleInput);
    await user.type(titleInput, "Organized Final");
    await user.click(screen.getByRole("button", { name: "draft" }));
    await user.click(screen.getByRole("button", { name: "Apply" }));

    expect(updateObject).toHaveBeenCalledTimes(1);
    expect(updateObject).toHaveBeenCalledWith("object-1", {
      title: "Organized Final",
      description: "Useful summary",
      tags: ["research"],
    });
    expect(onApplied).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
