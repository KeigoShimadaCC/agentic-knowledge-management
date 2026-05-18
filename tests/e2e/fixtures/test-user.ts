import { request, type APIRequestContext, type BrowserContext } from "@playwright/test";

const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8001";
const webURL = process.env.E2E_WEB_URL ?? "http://127.0.0.1:3000";
const email = process.env.E2E_USER_EMAIL ?? process.env.DEMO_SEED_EMAIL ?? "demo@example.com";
const password = process.env.E2E_USER_PASSWORD ?? process.env.DEMO_SEED_PASSWORD ?? "demo-demo-demo";

export interface TestUser {
  id: string;
  email: string;
  displayName: string;
  api: APIRequestContext;
  cookie: string;
  password: string;
}

export async function createTestUser(): Promise<TestUser> {
  const api = await request.newContext({ baseURL: apiURL });
  const login = await api.post("/api/v1/auth/login", {
    data: { email, password },
  });
  if (!login.ok()) {
    throw new Error(`/auth/login failed: ${login.status()} ${await login.text()}`);
  }

  const meRes = await api.get("/api/v1/auth/me");
  if (!meRes.ok()) {
    throw new Error(`/auth/me failed: ${meRes.status()} ${await meRes.text()}`);
  }
  const body = (await meRes.json()) as { user: { id: string; email: string; display_name: string } };
  const state = await api.storageState();
  const sessionCookie = state.cookies.find((cookie) => cookie.name === "kos_session")?.value ?? "";
  return {
    id: body.user.id,
    email: body.user.email,
    displayName: body.user.display_name ?? "",
    cookie: sessionCookie,
    password,
    api,
  };
}

export async function addUserCookie(context: BrowserContext, cookie: string) {
  if (!cookie) return;
  const webHost = new URL(webURL).hostname;
  const apiHost = new URL(apiURL).hostname;
  const hosts = Array.from(new Set([webHost, apiHost]));
  await context.addCookies(
    hosts.map((host) => ({
      name: "kos_session",
      value: cookie,
      domain: host,
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
      secure: false,
    }))
  );
}

export async function softDeleteAllObjects(api: APIRequestContext) {
  const response = await api.get("/api/v1/objects?limit=100");
  if (!response.ok()) return;
  const body = (await response.json()) as { items?: Array<{ id: string }> };
  await Promise.all((body.items ?? []).map((object) => api.delete(`/api/v1/objects/${object.id}`)));
}
