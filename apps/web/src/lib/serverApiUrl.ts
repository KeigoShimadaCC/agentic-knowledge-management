import { cookies } from "next/headers";

/**
 * Base URL for server-side fetches to FastAPI (RSC, Route Handlers, `next.config` rewrites).
 * In Docker Compose, set `API_URL=http://api:8000`. On the host with `pnpm dev`, use
 * `http://127.0.0.1:8001` when the API container publishes 8001.
 */
export function getServerApiUrl(): string {
  return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export function getServerApiHeaders(): HeadersInit {
  const session = cookies().get("kos_session")?.value;
  return session ? { Cookie: `kos_session=${session}` } : {};
}
