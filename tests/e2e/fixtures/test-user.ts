import { request, type APIRequestContext, type BrowserContext } from "@playwright/test";

const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8001";

export interface TestUser {
  id: string;
  email: string;
  displayName: string;
  api: APIRequestContext;
  // kept for compatibility but always empty — no session cookie needed
  cookie: string;
  password: string;
}

export async function createTestUser(): Promise<TestUser> {
  const api = await request.newContext({ baseURL: apiURL });
  const meRes = await api.get("/api/v1/auth/me");
  if (!meRes.ok()) {
    throw new Error(`/auth/me failed: ${meRes.status()} ${await meRes.text()}`);
  }
  const body = (await meRes.json()) as { user: { id: string; email: string; display_name: string } };
  return {
    id: body.user.id,
    email: body.user.email,
    displayName: body.user.display_name ?? "",
    cookie: "",
    password: "",
    api,
  };
}

// No-op: no cookie auth anymore
export async function addUserCookie(_context: BrowserContext, _cookie: string) {}

export async function softDeleteAllObjects(api: APIRequestContext) {
  const response = await api.get("/api/v1/objects?limit=100");
  if (!response.ok()) return;
  const body = (await response.json()) as { items?: Array<{ id: string }> };
  await Promise.all((body.items ?? []).map((object) => api.delete(`/api/v1/objects/${object.id}`)));
}
