import { request, type APIRequestContext, type BrowserContext } from "@playwright/test";

const apiURL = process.env.E2E_API_URL ?? "http://127.0.0.1:8001";

export interface TestUser {
  id: string;
  email: string;
  password: string;
  displayName: string;
  cookie: string;
  api: APIRequestContext;
}

function sessionCookieValue(setCookie: string | null): string {
  const match = setCookie?.match(/kos_session=([^;]+)/);
  if (!match) throw new Error("API did not return kos_session cookie");
  return match[1];
}

export async function createTestUser(): Promise<TestUser> {
  const email = `e2e-${crypto.randomUUID()}@example.com`;
  const password = "e2e-password";
  const displayName = "E2E User";
  const bootstrap = await request.newContext({ baseURL: apiURL });
  const response = await bootstrap.post("/api/v1/auth/register", {
    data: { email, password, display_name: displayName },
  });
  if (!response.ok()) {
    throw new Error(`Failed to register test user: ${response.status()} ${await response.text()}`);
  }
  const body = (await response.json()) as { user: { id: string } };
  const cookie = sessionCookieValue(response.headers()["set-cookie"] ?? null);
  await bootstrap.dispose();

  const api = await request.newContext({
    baseURL: apiURL,
    extraHTTPHeaders: { Cookie: `kos_session=${cookie}` },
  });

  return { id: body.user.id, email, password, displayName, cookie, api };
}

export async function addUserCookie(context: BrowserContext, cookie: string) {
  await context.addCookies([
    {
      name: "kos_session",
      value: cookie,
      domain: "localhost",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
}

export async function softDeleteAllObjects(api: APIRequestContext) {
  const response = await api.get("/api/v1/objects?limit=100");
  if (!response.ok()) return;
  const body = (await response.json()) as { items?: Array<{ id: string }> };
  await Promise.all((body.items ?? []).map((object) => api.delete(`/api/v1/objects/${object.id}`)));
}
