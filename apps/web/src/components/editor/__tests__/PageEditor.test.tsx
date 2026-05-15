import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PageEditor } from "@/components/editor/PageEditor";
import { renderWithProviders } from "@/test/render";

vi.mock("@/components/editor/SourcePicker", () => ({
  SourcePicker: () => null,
}));

describe("PageEditor", () => {
  it("mounts Tiptap with an empty document and emits text updates", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();

    renderWithProviders(<PageEditor initialContent={{}} onUpdate={onUpdate} />, {
      withWorkspace: false,
    });

    const editor = document.querySelector(".ProseMirror");
    expect(editor).toBeInTheDocument();

    (editor as HTMLElement).focus();
    await user.keyboard("Heading text");

    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
    expect(onUpdate.mock.calls.at(-1)?.[1]).toContain("Heading text");
    expect(screen.getByRole("button", { name: "Heading 1" })).toBeInTheDocument();
  });
});
