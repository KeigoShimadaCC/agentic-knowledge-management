import { fireEvent, render, screen } from "@testing-library/react";

import { InterviewStoryPanel } from "@/components/projects/InterviewStoryPanel";
import { projectFixture, storyFixture } from "./fixtures";

vi.mock("@/lib/api", () => ({
  generateInterviewStory: vi.fn(),
  saveInterviewStory: vi.fn(),
  deleteInterviewStory: vi.fn(),
}));
const useInterviewStories = vi.fn();
vi.mock("@/lib/hooks/useProjects", () => ({
  useInterviewStories: (...args: unknown[]) => useInterviewStories(...args),
}));

describe("InterviewStoryPanel", () => {
  beforeEach(() => {
    useInterviewStories.mockReturnValue({ stories: [storyFixture], mutate: vi.fn() });
  });

  it("renders STAR sections and word count", () => {
    render(<InterviewStoryPanel projectId="project-1" project={projectFixture} />);

    fireEvent.click(screen.getByText(/technical · Staff Engineer/i));

    expect(screen.getByText("Situation")).toBeInTheDocument();
    expect(screen.getByText("Task")).toBeInTheDocument();
    expect(screen.getByText("Action")).toBeInTheDocument();
    expect(screen.getByText("Result")).toBeInTheDocument();
    expect(screen.getByText(/32 words/)).toBeInTheDocument();
  });

  it("passes question type filter to hook", () => {
    render(<InterviewStoryPanel projectId="project-1" project={projectFixture} />);

    fireEvent.click(screen.getByRole("button", { name: "technical" }));

    expect(useInterviewStories).toHaveBeenLastCalledWith("project-1", "technical");
  });
});
