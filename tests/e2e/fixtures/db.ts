import { randomUUID } from "node:crypto";
import { Pool } from "pg";

const databaseUrl =
  process.env.E2E_DATABASE_URL ?? "postgresql://kos:kospass@127.0.0.1:5433/knowledgeos";

const pool = new Pool({ connectionString: databaseUrl });

export async function createSuccessfulAgentRun(userId: string, agentType: string) {
  const runId = randomUUID();
  await pool.query(
    `
      INSERT INTO agent_runs (
        id,
        user_id,
        status,
        agent_type,
        input,
        output,
        model,
        finished_at
      )
      VALUES ($1, $2, 'success', $3, $4::jsonb, $5::jsonb, 'gpt-4o-mini', now())
    `,
    [
      runId,
      userId,
      agentType,
      JSON.stringify({ context: { seeded_by: "playwright" }, temperature: 0.2 }),
      JSON.stringify({ text: "Canned E2E summary." }),
    ]
  );
  return runId;
}

export async function getAgentRun(runId: string) {
  const result = await pool.query<{
    id: string;
    agent_type: string;
    status: string;
  }>(
    `
      SELECT id, agent_type, status
      FROM agent_runs
      WHERE id = $1
    `,
    [runId]
  );
  return result.rows[0] ?? null;
}

export async function closeDatabase() {
  await pool.end();
}
