export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface ObjectOut {
  id: string;
  user_id: string;
  kind: "page" | "asset" | "note" | "bookmark" | "collection";
  title: string;
  description: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  is_pinned: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface PageOut {
  id: string;
  content_json: Record<string, unknown>;
  content_text: string;
  word_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AssetOut {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  storage_path: string;
  status: "uploading" | "ready" | "error";
  width: number | null;
  height: number | null;
  duration_secs: number | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface AuthResponse {
  user: User;
}

export interface PageCreateResponse {
  object: ObjectOut;
  page: PageOut;
}

export interface AssetUploadResponse {
  object: ObjectOut;
  asset: AssetOut;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}
