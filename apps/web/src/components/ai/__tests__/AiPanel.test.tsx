import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { AiPanel } from "@/components/ai/AiPanel";
import { API_BASE } from "@/test/msw/handlers";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/render";

describe("AiPanel", () => {
  it("summarizes an object and renders the result", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_BASE}/api/v1/ai/summarize`, () =>
        HttpResponse.json({
          summary: "Concise generated summary.",
          agent_run_id: "run-1",
          cached: false,
        })
      )
    );

    renderWithProviders(<AiPanel objectId="page-1" />);

    await user.click(screen.getByRole("button", { name: "Summarize" }));

    expect(await screen.findByText("Concise generated summary.")).toBeInTheDocument();
  });

  it("shows an AI-disabled error when the backend returns 503", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`${API_BASE}/api/v1/ai/summarize`, () =>
        HttpResponse.json({ detail: "ai_disabled" }, { status: 503 })
      )
    );

    renderWithProviders(<AiPanel objectId="page-1" />);

    await user.click(screen.getByRole("button", { name: "Summarize" }));

    await waitFor(() => expect(screen.getByText("ai_disabled")).toBeInTheDocument());
  });
});
