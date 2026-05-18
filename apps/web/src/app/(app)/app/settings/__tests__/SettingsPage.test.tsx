import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import SettingsPage from "../page";
import { API_BASE } from "@/test/msw/handlers";
import { sampleSettingsResponse } from "@/test/msw/fixtures/settings";
import { server } from "@/test/msw/server";
import { renderWithProviders } from "@/test/render";
import type { PromptOut } from "@/types";

describe("SettingsPage", () => {
  it("renders settings section tabs", async () => {
    renderWithProviders(<SettingsPage />, { withWorkspace: false });

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AI Providers" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Feature Models" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prompts" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "MCP" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Background AI" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Server/Diagnostics" })).toBeInTheDocument();
  });

  it("saves and resets a prompt override", async () => {
    const user = userEvent.setup();
    let prompt: PromptOut = sampleSettingsResponse.prompts[0]!;

    server.use(
      http.get(`${API_BASE}/api/v1/settings`, () =>
        HttpResponse.json({
          ...sampleSettingsResponse,
          prompts: [prompt],
        })
      ),
      http.patch(`${API_BASE}/api/v1/settings/prompts/summarize.page`, async ({ request }) => {
        const body = (await request.json()) as { template: string };
        prompt = {
          ...prompt,
          has_override: true,
          effective_template: body.template,
          override_template: body.template,
        };
        return HttpResponse.json(prompt);
      }),
      http.post(`${API_BASE}/api/v1/settings/prompts/summarize.page/reset`, () => {
        prompt = {
          ...prompt,
          has_override: false,
          effective_template: prompt.default_template,
          override_template: null,
        };
        return HttpResponse.json(prompt);
      })
    );

    renderWithProviders(<SettingsPage />, { withWorkspace: false });
    await screen.findByRole("heading", { name: "Settings" });

    await user.click(screen.getByRole("button", { name: "Prompts" }));
    const promptCard = screen.getByRole("heading", { name: "Summarize Page" }).closest("article");
    expect(promptCard).not.toBeNull();

    const editor = within(promptCard as HTMLElement);
    const textarea = editor.getByRole("textbox");
    await user.clear(textarea);
    await user.type(textarea, "Custom summary prompt: {content}");
    await user.click(editor.getByRole("button", { name: "Save" }));

    expect(await editor.findByText("Override")).toBeInTheDocument();

    await user.click(editor.getByRole("button", { name: "Reset" }));
    expect(editor.queryByText("Override")).not.toBeInTheDocument();
  });
});
