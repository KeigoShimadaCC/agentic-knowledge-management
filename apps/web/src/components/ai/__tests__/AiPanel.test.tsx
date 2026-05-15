import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AiPanel } from "@/components/ai/AiPanel";
import { aiSummarize } from "@/lib/api";
import { renderWithProviders } from "@/test/render";
import { ApiError } from "@/types";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    aiSummarize: vi.fn(),
    aiExtractClaims: vi.fn(),
    aiExtractTasks: vi.fn(),
    aiSuggestLinks: vi.fn(),
    aiAnswer: vi.fn(),
    createEdge: vi.fn(),
  };
});

describe("AiPanel", () => {
  it("summarizes an object and renders the result", async () => {
    const user = userEvent.setup();
    vi.mocked(aiSummarize).mockResolvedValue({
      summary: "Concise generated summary.",
      agent_run_id: "run-1",
      cached: false,
    });

    renderWithProviders(<AiPanel objectId="page-1" />);

    await user.click(screen.getByRole("button", { name: "Summarize" }));

    expect(await screen.findByText("Concise generated summary.")).toBeInTheDocument();
    expect(aiSummarize).toHaveBeenCalledWith("page-1");
  });

  it("shows an AI-disabled error when the backend returns 503", async () => {
    const user = userEvent.setup();
    vi.mocked(aiSummarize).mockRejectedValue(new ApiError(503, "AI disabled"));

    renderWithProviders(<AiPanel objectId="page-1" />);

    await user.click(screen.getByRole("button", { name: "Summarize" }));

    await waitFor(() => expect(screen.getByText("AI disabled")).toBeInTheDocument());
  });
});
