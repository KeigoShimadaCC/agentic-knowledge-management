import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  WorkspaceLiteProvider,
  useWorkspaceLite,
  type PaneState,
} from "@/components/workspace/WorkspaceLiteProvider";
import { PaneContainer } from "@/components/workspace/PaneContainer";
import { renderWithProviders } from "@/test/render";

vi.mock("@/components/workspace/ObjectPaneViewer", () => ({
  ObjectPaneViewer: ({ id }: { id: string }) => <div>viewer-{id}</div>,
}));
vi.mock("@/components/workspace/LinkPaneModal", () => ({
  LinkPaneModal: () => <div data-testid="link-modal" />,
}));
vi.mock("@/lib/objectRouting", () => ({
  objectRoute: (_kind: string, id: string) => `/app/${id}`,
  objectKindLabel: (kind: string) => kind,
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", () => ({ createWorkspace: vi.fn(), getWorkspace: vi.fn() }));

const sidePaneState: PaneState = {
  id: "pane-1",
  objectId: "obj-abc",
  objectKind: "page",
  title: "Alpha Page",
  mode: "read",
  sizePct: 40,
};

function HarnessWithPanes({ pane, isLast = true }: { pane: PaneState; isLast?: boolean }) {
  return (
    <WorkspaceLiteProvider>
      <PaneContainer pane={pane} isLast={isLast} />
    </WorkspaceLiteProvider>
  );
}

function renderPane(pane = sidePaneState, isLast = true) {
  return renderWithProviders(<HarnessWithPanes pane={pane} isLast={isLast} />, {
    withWorkspace: false,
  });
}

describe("PaneContainer", () => {
  it("renders kind badge and title for a populated pane", () => {
    renderPane();
    expect(screen.getByText("page")).toBeInTheDocument();
    expect(screen.getByText("Alpha Page")).toBeInTheDocument();
  });

  it("shows + Add pane button on last pane when panes < 4", () => {
    renderPane(sidePaneState, true);
    expect(screen.getByRole("button", { name: /add pane/i })).toBeInTheDocument();
  });

  it("hides + Add pane button when isLast=false", () => {
    renderPane(sidePaneState, false);
    expect(screen.queryByRole("button", { name: /add pane/i })).not.toBeInTheDocument();
  });

  it("shows Close pane button", () => {
    renderPane();
    expect(screen.getByRole("button", { name: /close pane/i })).toBeInTheDocument();
  });

  it("renders empty state when pane has no objectId", () => {
    const emptyPane: PaneState = { ...sidePaneState, objectId: null, objectKind: null, title: "" };
    renderPane(emptyPane);
    expect(screen.getByText(/empty pane/i)).toBeInTheDocument();
  });

  it("does NOT show link button when no other panes have objects", () => {
    renderPane();
    expect(screen.queryByRole("button", { name: /link to another pane/i })).not.toBeInTheDocument();
  });
});
