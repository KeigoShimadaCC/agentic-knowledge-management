import { Pool } from "pg";

const databaseUrl =
  process.env.E2E_DATABASE_URL ?? "postgresql://kos:kospass@127.0.0.1:5433/knowledgeos";

const pool = new Pool({ connectionString: databaseUrl });

export async function getLatestAgentRun(userId: string, agentType: string) {
  const result = await pool.query<{
    id: string;
    agent_type: string;
    status: string;
  }>(
    `
      SELECT id, agent_type, status
      FROM agent_runs
      WHERE user_id = $1 AND agent_type = $2
      ORDER BY created_at DESC
      LIMIT 1
    `,
    [userId, agentType]
  );
  return result.rows[0] ?? null;
}

export async function closeDatabase() {
  await pool.end();
}
