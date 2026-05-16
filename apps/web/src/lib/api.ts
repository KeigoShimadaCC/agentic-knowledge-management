import type {
  AnswerResponse,
  AssetUploadResponse,
  AuthResponse,
  ChatImportResponse,
  ChatOut,
  ChatProvider,
  ChatRawFormat,
  EdgeCreate,
  EdgeWithObjectsOut,
  EdgeOut,
  ExtractProjectRequest,
  ExtractProjectResponse,
  ExtractResponse,
  GenerateInterviewStoryRequest,
  GenerateInterviewStoryResponse,
  GenerateResumeBulletsRequest,
  GenerateResumeBulletsResponse,
  InterviewStoryOut,
  ObjectOut,
  PageCreateResponse,
  PageOut,
  PaginatedResponse,
  HybridSearchResponse,
  ProjectCreate,
  ProjectOut,
  ProjectUpdate,
  RelatedObjectOut,
  ResumeBulletSetOut,
  SaveInterviewStoryRequest,
  SaveResumeBulletSetRequest,
  SourceCreate,
  SourceOut,
  SearchResponse,
  StructuredChatSummary,
  StructuredSummaryApplyResponse,
  StructuredSummaryPreviewResponse,
  SuggestLinksResponse,
  SummarizeResponse,
  TriageResponse,
  WorkspaceOut,
  WorkspaceCreate,
  WorkspaceUpdate,
} from "@/types";
import { ApiError } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** FastAPI uses string | object[] | object for `detail`; normalize for ApiError.message. */
function formatErrorDetail(payload: unknown, fallback: string): string {
  if (payload === null || payload === undefined) {
    return fallback;
  }
  if (typeof payload === "string") {
    return payload;
  }
  if (typeof payload === "number" || typeof payload === "boolean") {
    return String(payload);
  }
  if (Array.isArray(payload)) {
    const parts = payload.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const row = item as { loc?: unknown[]; msg?: unknown };
        const loc =
          Array.isArray(row.loc) && row.loc.length > 0
            ? `${row.loc.map(String).join(".")}: `
            : "";
        return `${loc}${String(row.msg ?? "")}`;
      }
      try {
        return JSON.stringify(item);
      } catch {
        return String(item);
      }
    });
    return parts.filter(Boolean).join("; ") || fallback;
  }
  if (typeof payload === "object") {
    try {
      return JSON.stringify(payload);
    } catch {
      return fallback;
    }
  }
  return String(payload);
}

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
    const fallback = res.statusText?.trim() || `Request failed (${res.status})`;
    let detailPayload: unknown = fallback;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        detailPayload = (body as { detail: unknown }).detail;
      } else if (body !== null && body !== undefined) {
        detailPayload = body;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, formatErrorDetail(detailPayload, fallback));
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

export async function listTrashObjects(): Promise<ObjectOut[]> {
  return request<ObjectOut[]>("/api/v1/objects/trash");
}

export async function restoreObject(id: string): Promise<ObjectOut> {
  return request<ObjectOut>(`/api/v1/objects/${id}/restore`, { method: "POST" });
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

export const listChats = (params?: { provider?: string; q?: string }) =>
  apiFetch<ChatOut[]>(
    "/api/v1/chats" +
      (params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "")
  );

export const getChat = (id: string) => apiFetch<ChatOut>(`/api/v1/chats/${id}`);

export async function importChatContent(data: {
  content: string;
  provider: ChatProvider;
  title?: string;
  raw_format?: ChatRawFormat;
}): Promise<ChatImportResponse> {
  return apiFetch<ChatImportResponse>("/api/v1/chats/import", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function importChatFile(data: {
  file: File;
  provider: ChatProvider;
  title?: string;
}): Promise<ChatImportResponse> {
  const formData = new FormData();
  formData.append("file", data.file);
  formData.append("provider", data.provider);
  if (data.title) formData.append("title", data.title);
  const res = await fetch(`${BASE}/api/v1/chats/import`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, (err as { detail: string }).detail);
  }
  return res.json() as Promise<ChatImportResponse>;
}

export const getRawChatUrl = (id: string) => `${BASE}/api/v1/chats/${id}/raw`;

export const generateStructuredChatSummary = (id: string) =>
  apiFetch<StructuredSummaryPreviewResponse>(`/api/v1/chats/${id}/structured-summary`, {
    method: "POST",
  });

export const getStructuredChatSummary = (id: string) =>
  apiFetch<StructuredSummaryPreviewResponse>(`/api/v1/chats/${id}/structured-summary`);

export const applyStructuredChatSummary = (
  id: string,
  structured_summary?: StructuredChatSummary
) =>
  apiFetch<StructuredSummaryApplyResponse>(`/api/v1/chats/${id}/structured-summary/apply`, {
    method: "POST",
    body: JSON.stringify({
      structured_summary,
      create_claims: true,
      create_tasks: true,
      create_concepts: false,
      link_existing_objects: true,
    }),
  });

export const createEdge = (data: EdgeCreate) =>
  apiFetch<EdgeOut>("/api/v1/edges", { method: "POST", body: JSON.stringify(data) });

export const listEdges = (params?: { source_id?: string; target_id?: string; kind?: string }) =>
  apiFetch<EdgeOut[]>(
    "/api/v1/edges" +
      (params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "")
  );

export const deleteEdge = (id: string) =>
  apiFetch<EdgeOut>(`/api/v1/edges/${id}`, { method: "DELETE" });

export async function keywordSearch(
  q: string,
  opts?: { kind?: string; limit?: number; objectIds?: string[] }
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q });
  if (opts?.kind) params.set("kind", opts.kind);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.objectIds?.length) {
    opts.objectIds.forEach((id) => params.append("object_ids", id));
  }
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
  opts?: { kind?: string; limit?: number; debug?: boolean; objectIds?: string[] }
): Promise<HybridSearchResponse> {
  return request<HybridSearchResponse>("/api/v1/search/hybrid", {
    method: "POST",
    body: JSON.stringify({
      q,
      kind: opts?.kind ?? null,
      limit: opts?.limit ?? 10,
      debug: opts?.debug ?? false,
      object_ids: opts?.objectIds && opts.objectIds.length > 0 ? opts.objectIds : null,
    }),
  });
}

export async function getObjectBacklinks(objectId: string): Promise<EdgeWithObjectsOut[]> {
  return request<EdgeWithObjectsOut[]>(`/api/v1/objects/${objectId}/backlinks`);
}

export async function getObjectRelated(
  objectId: string,
  depth = 1
): Promise<RelatedObjectOut[]> {
  const params = new URLSearchParams({ depth: String(depth), limit: "15" });
  return request<RelatedObjectOut[]>(`/api/v1/objects/${objectId}/related?${params}`);
}

// ── AI feature functions ──────────────────────────────────────────────────────

export async function aiSummarize(objectId: string, force = false): Promise<SummarizeResponse> {
  return request<SummarizeResponse>("/api/v1/ai/summarize", {
    method: "POST",
    body: JSON.stringify({ object_id: objectId, force }),
  });
}

export async function aiExtractClaims(objectId: string): Promise<ExtractResponse> {
  return request<ExtractResponse>("/api/v1/ai/extract-claims", {
    method: "POST",
    body: JSON.stringify({ object_id: objectId }),
  });
}

export async function aiExtractTasks(objectId: string): Promise<ExtractResponse> {
  return request<ExtractResponse>("/api/v1/ai/extract-tasks", {
    method: "POST",
    body: JSON.stringify({ object_id: objectId }),
  });
}

export async function aiSuggestLinks(
  objectId: string,
  limit = 5
): Promise<SuggestLinksResponse> {
  return request<SuggestLinksResponse>("/api/v1/ai/suggest-links", {
    method: "POST",
    body: JSON.stringify({ object_id: objectId, limit }),
  });
}

export async function aiAnswer(
  q: string,
  kind?: string,
  object_ids?: string[]
): Promise<AnswerResponse> {
  return request<AnswerResponse>("/api/v1/ai/answer", {
    method: "POST",
    body: JSON.stringify({
      q,
      kind: kind ?? null,
      object_ids: object_ids && object_ids.length > 0 ? object_ids : null,
    }),
  });
}

export async function aiTriage(objectId: string): Promise<TriageResponse> {
  return request<TriageResponse>("/api/v1/ai/triage", {
    method: "POST",
    body: JSON.stringify({ object_id: objectId }),
  });
}

export async function getInbox(
  params: { limit?: number; offset?: number } = {}
): Promise<PaginatedResponse<ObjectOut>> {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return request<PaginatedResponse<ObjectOut>>(`/api/v1/ai/inbox${query ? `?${query}` : ""}`);
}

export async function aiComplete(
  contextBefore: string,
  instruction: "continue" | "expand" = "continue",
  objectId?: string,
  maxTokens = 200
): Promise<{ completion: string; agent_run_id: string }> {
  return request<{ completion: string; agent_run_id: string }>("/api/v1/ai/complete", {
    method: "POST",
    body: JSON.stringify({
      context_before: contextBefore,
      instruction,
      object_id: objectId ?? null,
      max_tokens: maxTokens,
    }),
  });
}

export async function aiTransform(
  text: string,
  instruction: "improve" | "concise" | "grammar" | "summarize",
  objectId?: string
): Promise<{ result: string; agent_run_id: string }> {
  return request<{ result: string; agent_run_id: string }>("/api/v1/ai/transform", {
    method: "POST",
    body: JSON.stringify({ text, instruction, object_id: objectId ?? null }),
  });
}

export async function getObject(id: string): Promise<ObjectOut> {
  return request<ObjectOut>(`/api/v1/objects/${id}`);
}

export async function updateObject(
  id: string,
  data: {
    title?: string;
    description?: string;
    tags?: string[];
    is_pinned?: boolean;
    is_archived?: boolean;
  }
): Promise<ObjectOut> {
  return request<ObjectOut>(`/api/v1/objects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteObject(id: string): Promise<ObjectOut> {
  return request<ObjectOut>(`/api/v1/objects/${id}`, { method: "DELETE" });
}

export async function archiveObject(id: string): Promise<ObjectOut> {
  return request<ObjectOut>(`/api/v1/objects/${id}/archive`, { method: "POST" });
}

// ── Workspace API ─────────────────────────────────────────────────────────

export async function listWorkspaces(params?: {
  limit?: number;
  offset?: number;
  pinned_only?: boolean;
}): Promise<PaginatedResponse<WorkspaceOut>> {
  const qs = new URLSearchParams();
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  if (params?.pinned_only) qs.set("pinned_only", "true");
  const query = qs.toString();
  return request<PaginatedResponse<WorkspaceOut>>(
    `/api/v1/workspaces${query ? `?${query}` : ""}`
  );
}

export async function createWorkspace(
  body: WorkspaceCreate
): Promise<WorkspaceOut> {
  return request<WorkspaceOut>("/api/v1/workspaces", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getWorkspace(id: string): Promise<WorkspaceOut> {
  return request<WorkspaceOut>(`/api/v1/workspaces/${id}`);
}

export async function updateWorkspace(
  id: string,
  body: WorkspaceUpdate
): Promise<WorkspaceOut> {
  return request<WorkspaceOut>(`/api/v1/workspaces/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteWorkspace(id: string): Promise<void> {
  await request<void>(`/api/v1/workspaces/${id}`, { method: "DELETE" });
}

export async function restoreWorkspace(id: string): Promise<WorkspaceOut> {
  return request<WorkspaceOut>(`/api/v1/workspaces/${id}/restore`, {
    method: "POST",
  });
}

// ── Career memory API ───────────────────────────────────────────────────────

export async function listProjects(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  skill?: string;
  include_archived?: boolean;
}): Promise<PaginatedResponse<ProjectOut>> {
  const qs = new URLSearchParams();
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  if (params?.status) qs.set("status", params.status);
  if (params?.skill) qs.set("skill", params.skill);
  if (params?.include_archived !== undefined) {
    qs.set("include_archived", String(params.include_archived));
  }
  const query = qs.toString();
  return request<PaginatedResponse<ProjectOut>>(`/api/v1/projects${query ? `?${query}` : ""}`);
}

export async function createProject(data: ProjectCreate): Promise<ProjectOut> {
  return request<ProjectOut>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getProject(id: string): Promise<ProjectOut> {
  return request<ProjectOut>(`/api/v1/projects/${id}`);
}

export async function updateProject(id: string, data: ProjectUpdate): Promise<ProjectOut> {
  return request<ProjectOut>(`/api/v1/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteProject(id: string): Promise<void> {
  await request<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}

export async function extractProject(
  payload: ExtractProjectRequest
): Promise<ExtractProjectResponse> {
  return request<ExtractProjectResponse>("/api/v1/ai/extract-project", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateResumeBullets(
  payload: GenerateResumeBulletsRequest
): Promise<GenerateResumeBulletsResponse> {
  return request<GenerateResumeBulletsResponse>("/api/v1/ai/generate-resume-bullets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generateInterviewStory(
  payload: GenerateInterviewStoryRequest
): Promise<GenerateInterviewStoryResponse> {
  return request<GenerateInterviewStoryResponse>("/api/v1/ai/generate-interview-story", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listResumeBulletSets(
  projectId: string,
  params?: { limit?: number; offset?: number }
): Promise<ResumeBulletSetOut[]> {
  const qs = new URLSearchParams();
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return request<ResumeBulletSetOut[]>(
    `/api/v1/projects/${projectId}/resume-bullet-sets${query ? `?${query}` : ""}`
  );
}

export async function saveResumeBulletSet(
  projectId: string,
  payload: SaveResumeBulletSetRequest
): Promise<ResumeBulletSetOut> {
  return request<ResumeBulletSetOut>(`/api/v1/projects/${projectId}/resume-bullet-sets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteResumeBulletSet(id: string): Promise<void> {
  await request<void>(`/api/v1/resume-bullet-sets/${id}`, { method: "DELETE" });
}

export async function listInterviewStories(
  projectId: string,
  params?: { question_type?: string; limit?: number; offset?: number }
): Promise<InterviewStoryOut[]> {
  const qs = new URLSearchParams();
  if (params?.question_type) qs.set("question_type", params.question_type);
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const query = qs.toString();
  return request<InterviewStoryOut[]>(
    `/api/v1/projects/${projectId}/interview-stories${query ? `?${query}` : ""}`
  );
}

export async function saveInterviewStory(
  projectId: string,
  payload: SaveInterviewStoryRequest
): Promise<InterviewStoryOut> {
  return request<InterviewStoryOut>(`/api/v1/projects/${projectId}/interview-stories`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteInterviewStory(id: string): Promise<void> {
  await request<void>(`/api/v1/interview-stories/${id}`, { method: "DELETE" });
}
