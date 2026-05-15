import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkspaceLiteProvider, useWorkspaceLite } from "@/components/workspace/WorkspaceLiteProvider";
import { WorkspaceSidePane } from "@/components/workspace/WorkspaceSidePane";
import { renderWithProviders } from "@/test/render";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/components/workspace/ObjectPaneViewer", () => ({
  ObjectPaneViewer: ({ title }: { title: string }) => <div>Pane content for {title}</div>,
}));

function WorkspaceHarness() {
  const { sidePaneObject, openSidePane, closeSidePane } = useWorkspaceLite();
  return (
    <>
      <button type="button" onClick={() => openSidePane({ id: "page-1", kind: "page", title: "Alpha Page" })}>
        Open pane
      </button>
      <button type="button" onClick={closeSidePane}>
        Close pane
      </button>
      <span>{sidePaneObject?.title ?? "No pane"}</span>
      <WorkspaceSidePane />
    </>
  );
}

describe("WorkspaceLiteProvider", () => {
  it("opens, rerenders, and closes the side pane with Escape", async () => {
    const user = userEvent.setup();
    const { rerender } = renderWithProviders(
      <WorkspaceLiteProvider>
        <WorkspaceHarness />
      </WorkspaceLiteProvider>,
      { withWorkspace: false }
    );

    await user.click(screen.getByRole("button", { name: "Open pane" }));
    expect(screen.getAllByText("Alpha Page")[0]).toBeInTheDocument();

    rerender(
      <WorkspaceLiteProvider>
        <WorkspaceHarness />
      </WorkspaceLiteProvider>
    );
    expect(screen.getAllByText("Alpha Page")[0]).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByText("No pane")).toBeInTheDocument();
  });
});
