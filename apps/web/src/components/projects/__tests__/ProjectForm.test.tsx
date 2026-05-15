import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { createProject } from "@/lib/api";
import { ProjectForm } from "@/components/projects/ProjectForm";
import { projectFixture } from "./fixtures";

vi.mock("@/lib/api", () => ({
  createProject: vi.fn(),
  updateProject: vi.fn(),
}));

describe("ProjectForm", () => {
  it("shows validation for an empty title", async () => {
    render(<ProjectForm mode="create" onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Title is required")).toBeInTheDocument();
  });

  it("validates period order", async () => {
    render(<ProjectForm mode="create" onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Bad dates" } });
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-02-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("End date must be after start date")).toBeInTheDocument();
  });

  it("submits normalized skills", async () => {
    vi.mocked(createProject).mockResolvedValue(projectFixture);
    render(<ProjectForm mode="create" onClose={vi.fn()} onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "KnowledgeOS" } });
    const skillInput = screen.getAllByPlaceholderText("Type and press Enter")[0]!;
    fireEvent.change(skillInput, { target: { value: "Python" } });
    fireEvent.keyDown(skillInput, { key: "Enter" });
    fireEvent.change(skillInput, { target: { value: " python " } });
    fireEvent.keyDown(skillInput, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(createProject).toHaveBeenCalled());
    expect(vi.mocked(createProject).mock.calls[0]?.[0]).toMatchObject({
      title: "KnowledgeOS",
      skills: ["python"],
    });
  });
});
