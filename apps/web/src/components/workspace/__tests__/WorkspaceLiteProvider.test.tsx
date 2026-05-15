import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  WorkspaceLiteProvider,
  useWorkspaceLite,
} from "@/components/workspace/WorkspaceLiteProvider";
import { renderWithProviders } from "@/test/render";

vi.mock("@/lib/api", () => ({
  createWorkspace: vi.fn().mockResolvedValue({
    id: "ws-1",
    name: "Test",
    layout: { version: 1, split: null, panes: [], active_pane_id: "main" },
  }),
  getWorkspace: vi.fn().mockResolvedValue({
    id: "ws-1",
    name: "Test",
    layout: {
      version: 1,
      split: "horizontal",
      panes: [
        { id: "main", object_id: null, object_kind: null, size_pct: 60, mode: "read" },
        { id: "pane-1", object_id: "obj-abc", object_kind: "page", size_pct: 40, mode: "read" },
      ],
      active_pane_id: "pane-1",
    },
  }),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

// Harness that exposes workspace state to assertions
function Harness() {
  const {
    panes,
    activePaneId,
    openSidePane,
    closeSidePane,
    addPane,
    removePane,
    sidePaneObject,
    loadWorkspace,
  } = useWorkspaceLite();
  return (
    <>
      <span data-testid="pane-count">{panes.length}</span>
      <span data-testid="active-pane">{activePaneId}</span>
      <span data-testid="side-object">{sidePaneObject?.title ?? "none"}</span>
      <button onClick={() => openSidePane({ id: "p1", kind: "page", title: "Page Alpha" })}>
        open-side
      </button>
      <button onClick={closeSidePane}>close-side</button>
      <button onClick={addPane}>add-pane</button>
      <button onClick={() => removePane(panes[1]?.id ?? "")}>remove-last</button>
      <button onClick={() => void loadWorkspace("ws-1")}>load-ws</button>
    </>
  );
}

function render() {
  return renderWithProviders(
    <WorkspaceLiteProvider>
      <Harness />
    </WorkspaceLiteProvider>,
    { withWorkspace: false }
  );
}

describe("WorkspaceLiteProvider — multi-pane state", () => {
  it("starts with one pane", () => {
    render();
    expect(screen.getByTestId("pane-count").textContent).toBe("1");
  });

  it("openSidePane adds a second pane and sets sidePaneObject", async () => {
    const user = userEvent.setup();
    render();
    await user.click(screen.getByRole("button", { name: "open-side" }));
    expect(screen.getByTestId("pane-count").textContent).toBe("2");
    expect(screen.getByTestId("side-object").textContent).toBe("Page Alpha");
  });

  it("closeSidePane removes side panes and clears sidePaneObject", async () => {
    const user = userEvent.setup();
    render();
    await user.click(screen.getByRole("button", { name: "open-side" }));
    await user.click(screen.getByRole("button", { name: "close-side" }));
    expect(screen.getByTestId("pane-count").textContent).toBe("1");
    expect(screen.getByTestId("side-object").textContent).toBe("none");
  });

  it("addPane adds up to 4 panes", async () => {
    const user = userEvent.setup();
    render();
    await user.click(screen.getByRole("button", { name: "add-pane" }));
    expect(screen.getByTestId("pane-count").textContent).toBe("2");
    await user.click(screen.getByRole("button", { name: "add-pane" }));
    await user.click(screen.getByRole("button", { name: "add-pane" }));
    expect(screen.getByTestId("pane-count").textContent).toBe("4");
    // 5th add is ignored
    await user.click(screen.getByRole("button", { name: "add-pane" }));
    expect(screen.getByTestId("pane-count").textContent).toBe("4");
  });

  it("removePane removes a side pane", async () => {
    const user = userEvent.setup();
    render();
    await user.click(screen.getByRole("button", { name: "add-pane" }));
    await user.click(screen.getByRole("button", { name: "remove-last" }));
    expect(screen.getByTestId("pane-count").textContent).toBe("1");
  });

  it("loadWorkspace restores panes from saved layout", async () => {
    const user = userEvent.setup();
    render();
    await act(async () => {
      await user.click(screen.getByRole("button", { name: "load-ws" }));
    });
    expect(screen.getByTestId("pane-count").textContent).toBe("2");
  });
});
