import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { generateResumeBullets, saveResumeBulletSet } from "@/lib/api";
import { ResumeBulletsPanel } from "@/components/projects/ResumeBulletsPanel";
import { ApiError } from "@/types";
import { bulletSetFixture, projectFixture } from "./fixtures";

vi.mock("@/lib/api", () => ({
  generateResumeBullets: vi.fn(),
  saveResumeBulletSet: vi.fn(),
  deleteResumeBulletSet: vi.fn(),
}));
vi.mock("@/lib/hooks/useProjects", () => ({
  useResumeBulletSets: () => ({ bulletSets: [bulletSetFixture], mutate: vi.fn() }),
}));
vi.mock("@/components/workspace/WorkspaceLiteProvider", () => ({
  useWorkspaceLite: () => ({ openSidePane: vi.fn() }),
}));

describe("ResumeBulletsPanel", () => {
  it("shows an AI disabled banner on 503", async () => {
    vi.mocked(generateResumeBullets).mockRejectedValue(new ApiError(503, "disabled"));
    render(<ResumeBulletsPanel projectId="project-1" project={projectFixture} />);

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    expect(await screen.findByText(/AI disabled/)).toBeInTheDocument();
  });

  it("renders preview bullets after generation", async () => {
    vi.mocked(generateResumeBullets).mockResolvedValue({
      project_id: "project-1",
      agent_run_id: "run-1",
      evidence_count: 1,
      bullets: bulletSetFixture.bullets,
    });
    render(<ResumeBulletsPanel projectId="project-1" project={projectFixture} />);

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    expect(await screen.findByText(/Built a retrieval system/)).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("saves preview payload", async () => {
    vi.mocked(generateResumeBullets).mockResolvedValue({
      project_id: "project-1",
      agent_run_id: "run-1",
      evidence_count: 1,
      bullets: bulletSetFixture.bullets,
    });
    vi.mocked(saveResumeBulletSet).mockResolvedValue(bulletSetFixture);
    render(<ResumeBulletsPanel projectId="project-1" project={projectFixture} />);

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    await screen.findByText(/Built a retrieval system/);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(saveResumeBulletSet).toHaveBeenCalled());
    expect(vi.mocked(saveResumeBulletSet).mock.calls[0]?.[1]).toMatchObject({
      bullets: bulletSetFixture.bullets,
      agent_run_id: "run-1",
    });
  });
});
