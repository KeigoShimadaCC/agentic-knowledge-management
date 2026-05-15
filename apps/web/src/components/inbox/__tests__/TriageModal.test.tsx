import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { TriageModal } from "@/components/inbox/TriageModal";
import { API_BASE } from "@/test/msw/handlers";
import { sampleObject } from "@/test/msw/fixtures";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/render";

describe("TriageModal", () => {
  it("toggles suggested tags, edits the title, and applies one object patch", async () => {
    const user = userEvent.setup();
    const onApplied = vi.fn();
    const onClose = vi.fn();
    let patchCount = 0;

    server.use(
      http.post(`${API_BASE}/api/v1/ai/triage`, () =>
        HttpResponse.json({
          suggested_tags: ["research", "draft"],
          suggested_title: "Organized Page",
          summary: "Useful summary",
          agent_run_id: "run-1",
        })
      ),
      http.patch(`${API_BASE}/api/v1/objects/object-1`, async ({ request }) => {
        patchCount += 1;
        const body = (await request.json()) as {
          title?: string;
          description?: string;
          tags?: string[];
        };
        expect(body).toEqual({
          title: "Organized Final",
          description: "Useful summary",
          tags: ["research"],
        });
        return HttpResponse.json({ ...sampleObject, title: "Organized Final" });
      })
    );

    renderWithProviders(
      <TriageModal object={sampleObject} onApplied={onApplied} onClose={onClose} />,
      { withWorkspace: false }
    );

    await user.click(screen.getByRole("button", { name: "Analyze with AI" }));
    const titleInput = await screen.findByDisplayValue("Organized Page");
    await user.clear(titleInput);
    await user.type(titleInput, "Organized Final");
    await user.click(screen.getByRole("button", { name: "draft" }));
    await user.click(screen.getByRole("button", { name: "Apply" }));

    expect(patchCount).toBe(1);
    expect(onApplied).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
