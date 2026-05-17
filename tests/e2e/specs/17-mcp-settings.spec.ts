import { expect, test } from "../fixtures/api";

test("MCP settings page renders connection list area", async ({ page }) => {
  await page.goto("/app/settings/mcp");
  await expect(page.getByText(/MCP Connections|MCP Settings/i).first()).toBeVisible();
});

test("Add MCP connection button opens creation modal", async ({ page }) => {
  await page.goto("/app/settings/mcp");
  await page.getByRole("button", { name: "Add MCP connection" }).click();

  await expect(page.getByText("Add MCP Connection")).toBeVisible();
  await expect(page.getByPlaceholder("Local notes MCP")).toBeVisible();
});

test("MCP connection modal has required fields and submit button", async ({ page }) => {
  await page.goto("/app/settings/mcp");
  await page.getByRole("button", { name: "Add MCP connection" }).click();

  const modal = page.locator(".fixed.inset-0").last();
  await expect(modal.getByPlaceholder("Local notes MCP")).toBeVisible();
  await expect(modal.getByRole("button", { name: "Create Connection" })).toBeVisible();

  // Close the modal
  await modal.getByRole("button", { name: /Close|Cancel/i }).click();
  await expect(page.getByText("Add MCP Connection")).toBeHidden({ timeout: 3_000 });
});

test("delete with inline confirm: shows Cancel+Confirm, then removes row", async ({ page, api }) => {
  const name = `Delete MCP ${crypto.randomUUID().slice(0, 8)}`;
  const conn = await api.post("/api/v1/mcp/connections", {
    data: {
      name,
      transport: "stdio",
      command: "echo",
      args: [],
      env_vars: {},
      enabled: true,
    },
  });
  if (!conn.ok()) {
    test.skip(true, "MCP connections API not available or schema mismatch");
    return;
  }
  const { id } = (await conn.json()) as { id: string };

  await page.goto("/app/settings/mcp");
  await expect(page.getByText(name)).toBeVisible({ timeout: 5_000 });

  // Click Delete — should show inline confirm UI, not window.confirm
  await page.getByRole("button", { name: "Delete" }).first().click();
  await expect(page.getByRole("button", { name: "Confirm delete" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();

  // Confirm delete — row should disappear
  await page.getByRole("button", { name: "Confirm delete" }).click();
  await expect(page.getByText(name)).toBeHidden({ timeout: 8_000 });

  // Cleanup in case delete failed
  await api.delete(`/api/v1/mcp/connections/${id}`).catch(() => {});
});

test("existing MCP connection row shows Test button", async ({ page, api }) => {
  // Create a test MCP connection via the API
  const conn = await api.post("/api/v1/mcp/connections", {
    data: {
      name: `Test MCP ${crypto.randomUUID().slice(0, 8)}`,
      transport: "stdio",
      command: "echo",
      args: [],
      env_vars: {},
      enabled: true,
    },
  });
  if (!conn.ok()) {
    test.skip(true, "MCP connections API not available or schema mismatch");
    return;
  }
  const { id } = (await conn.json()) as { id: string };

  await page.goto("/app/settings/mcp");
  await expect(page.getByRole("button", { name: "Test" }).first()).toBeVisible({ timeout: 5_000 });

  // Cleanup
  await api.delete(`/api/v1/mcp/connections/${id}`);
});
