import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { GraphPanel } from "@/components/graph/GraphPanel";
import { API_BASE } from "@/test/msw/handlers";
import { sampleBacklinks, sampleRelated } from "@/test/msw/fixtures";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/render";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("GraphPanel", () => {
  it("renders backlinks and switches to related and AI tabs", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API_BASE}/api/v1/objects/page-1/backlinks`, () =>
        HttpResponse.json(sampleBacklinks)
      ),
      http.get(`${API_BASE}/api/v1/objects/page-1/related`, () => HttpResponse.json(sampleRelated))
    );

    renderWithProviders(<GraphPanel objectId="page-1" refreshKey={0} />);

    expect(await screen.findByText("Source Page")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Related" }));
    expect(await screen.findByText("Related Source")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "AI" }));
    expect(screen.getByRole("button", { name: "Summarize" })).toBeInTheDocument();
  });

  it("renders the backlinks empty state", async () => {
    server.use(
      http.get(`${API_BASE}/api/v1/objects/page-1/backlinks`, () => HttpResponse.json([])),
      http.get(`${API_BASE}/api/v1/objects/page-1/related`, () => HttpResponse.json([]))
    );

    renderWithProviders(<GraphPanel objectId="page-1" refreshKey={0} />);

    await waitFor(() => expect(screen.getByText("No backlinks yet.")).toBeInTheDocument());
  });
});
