import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { WorkspaceLiteProvider } from "@/components/workspace/WorkspaceLiteProvider";
import { WorkspaceNameModal } from "@/components/workspace/WorkspaceNameModal";
import { renderWithProviders } from "@/test/render";

const mockCreateWorkspace = vi.fn().mockResolvedValue({
  id: "ws-new",
  name: "My Workspace",
  layout: { version: 1, split: null, panes: [], active_pane_id: "main" },
});

vi.mock("@/lib/api", () => ({
  createWorkspace: (...args: unknown[]) => mockCreateWorkspace(...args),
  getWorkspace: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function render(onClose = vi.fn()) {
  return renderWithProviders(
    <WorkspaceLiteProvider>
      <WorkspaceNameModal open onClose={onClose} />
    </WorkspaceLiteProvider>,
    { withWorkspace: false }
  );
}

describe("WorkspaceNameModal", () => {
  it("renders name input and Save button", () => {
    render();
    expect(screen.getByPlaceholderText("My research session")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
  });

  it("enables Save button when name is entered", async () => {
    const user = userEvent.setup();
    render();
    await user.type(screen.getByPlaceholderText("My research session"), "My WS");
    expect(screen.getByRole("button", { name: /save/i })).not.toBeDisabled();
  });

  it("calls createWorkspace and closes modal on save", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(onClose);
    await user.type(screen.getByPlaceholderText("My research session"), "Research Session");
    await user.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(mockCreateWorkspace).toHaveBeenCalled());
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it("closes without saving on Cancel", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(onClose);
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
    expect(mockCreateWorkspace).not.toHaveBeenCalled();
  });
});
