import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { once } from "node:events";
import { resolve } from "node:path";
import { expect, test } from "../fixtures/api";

const repoRoot = process.cwd().endsWith("tests/e2e")
  ? resolve(process.cwd(), "../..")
  : process.cwd();

function encodeMessage(message: unknown): string {
  return `${JSON.stringify(message)}\n`;
}

async function readMessage(
  process: ChildProcessWithoutNullStreams,
  stderr: string[]
): Promise<Record<string, unknown>> {
  let buffer = "";
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    const [chunk] = (await Promise.race([
      once(process.stdout, "data"),
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error("timeout")), 500)),
    ]).catch(() => [Buffer.from("")])) as [Buffer];
    if (!chunk.length) continue;
    buffer += chunk.toString("utf8");
    const newline = buffer.indexOf("\n");
    if (newline === -1) continue;

    return JSON.parse(buffer.slice(0, newline)) as Record<string, unknown>;
  }
  throw new Error(`Timed out waiting for MCP response. stderr:\n${stderr.join("")}`);
}

test("lists MCP read tools over stdio", async () => {
  const stderr: string[] = [];
  const child = spawn("uv", ["run", "--project", "services/mcp", "kos-mcp"], {
    cwd: repoRoot,
    env: {
      ...process.env,
      MCP_ENABLED: "true",
      MCP_API_BASE_URL: process.env.E2E_API_URL ?? "http://127.0.0.1:8001",
    },
    stdio: ["pipe", "pipe", "pipe"],
  });
  child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk.toString("utf8")));

  try {
    child.stdin.write(
      encodeMessage({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "knowledgeos-e2e", version: "0.1.0" },
        },
      })
    );
    const initialized = await readMessage(child, stderr);
    expect(initialized).toMatchObject({ id: 1 });

    child.stdin.write(encodeMessage({ jsonrpc: "2.0", method: "notifications/initialized" }));
    child.stdin.write(encodeMessage({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} }));
    const tools = await readMessage(child, stderr);
    const names = ((tools.result as { tools: Array<{ name: string }> }).tools ?? []).map(
      (tool) => tool.name
    );

    expect(names).toEqual(
      expect.arrayContaining(["search_objects", "get_object", "get_page", "get_source"])
    );
  } finally {
    child.kill();
  }
});
