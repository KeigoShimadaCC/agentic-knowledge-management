import type {
  AssetUploadResponse,
  AuthResponse,
  EdgeCreate,
  EdgeOut,
  ObjectOut,
  PageCreateResponse,
  PageOut,
  PaginatedResponse,
  HybridSearchResponse,
  SourceCreate,
  SourceOut,
  SearchResponse,
} from "@/types";
import { ApiError } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, (err as { detail: string }).detail);
  }
  return res.json() as Promise<T>;
}

export const apiFetch = request;

export async function getMe(): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/me");
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(
  email: string,
  password: string,
  display_name: string
): Promise<AuthResponse> {
  return request<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, display_name }),
  });
}

export async function logout(): Promise<void> {
  await request<{ ok: boolean }>("/api/v1/auth/logout", { method: "POST" });
}

export interface ListObjectsParams {
  kind?: string;
  tag?: string;
  q?: string;
  page?: number;
  limit?: number;
}

export async function listObjects(
  params: ListObjectsParams = {}
): Promise<PaginatedResponse<ObjectOut>> {
  const qs = new URLSearchParams();
  if (params.kind) qs.set("kind", params.kind);
  if (params.tag) qs.set("tag", params.tag);
  if (params.q) qs.set("q", params.q);
  if (params.page) qs.set("page", String(params.page));
  if (params.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return request<PaginatedResponse<ObjectOut>>(`/api/v1/objects${query ? `?${query}` : ""}`);
}

export async function createPage(title: string): Promise<PageCreateResponse> {
  return request<PageCreateResponse>("/api/v1/pages", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function getPage(id: string): Promise<PageOut> {
  return request<PageOut>(`/api/v1/pages/${id}`);
}

export async function updatePage(
  id: string,
  data: { title?: string; content_json?: Record<string, unknown>; content_text?: string }
): Promise<PageOut> {
  return request<PageOut>(`/api/v1/pages/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function uploadAsset(file: File): Promise<AssetUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE}/api/v1/assets/upload`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, (err as { detail: string }).detail);
  }
  return res.json() as Promise<AssetUploadResponse>;
}

export const listSources = (params?: { source_type?: string; ingestion_status?: string; q?: string }) =>
  apiFetch<SourceOut[]>(
    "/api/v1/sources" +
      (params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "")
  );

export const createSource = (data: SourceCreate) =>
  apiFetch<SourceOut>("/api/v1/sources", { method: "POST", body: JSON.stringify(data) });

export const getSource = (id: string) => apiFetch<SourceOut>(`/api/v1/sources/${id}`);

export const deleteSource = (id: string) =>
  apiFetch<SourceOut>(`/api/v1/sources/${id}`, { method: "DELETE" });

export const createEdge = (data: EdgeCreate) =>
  apiFetch<EdgeOut>("/api/v1/edges", { method: "POST", body: JSON.stringify(data) });

export const listEdges = (params?: { source_id?: string; target_id?: string; kind?: string }) =>
  apiFetch<EdgeOut[]>(
    "/api/v1/edges" +
      (params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "")
  );

export async function keywordSearch(
  q: string,
  opts?: { kind?: string; limit?: number }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q });
  if (opts?.kind) params.set("kind", opts.kind);
  if (opts?.limit) params.set("limit", String(opts.limit));
  return request<SearchResponse>(`/api/v1/search/keyword?${params}`);
}

export async function vectorSearch(
  q: string,
  opts?: { kind?: string; limit?: number }
): Promise<SearchResponse> {
  return request<SearchResponse>("/api/v1/search/vector", {
    method: "POST",
    body: JSON.stringify({ q, kind: opts?.kind ?? null, limit: opts?.limit ?? 10 }),
  });
}

export async function hybridSearch(
  q: string,
  opts?: { kind?: string; limit?: number }
): Promise<HybridSearchResponse> {
  return request<HybridSearchResponse>("/api/v1/search/hybrid", {
    method: "POST",
    body: JSON.stringify({ q, kind: opts?.kind ?? null, limit: opts?.limit ?? 10 }),
  });
}
