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

export type SourceType = "pdf" | "image" | "video" | "audio" | "youtube" | "web" | "csv" | "file";
export type IngestionStatus = "pending" | "running" | "ready" | "error";

export interface SourceOut {
  id: string;
  user_id: string;
  kind: string;
  title: string;
  description: string | null;
  tags: string[];
  is_pinned: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  source_type: SourceType;
  url: string | null;
  asset_id: string | null;
  ingestion_status: IngestionStatus;
  extracted_text: string | null;
  page_count: number | null;
  thumbnail_path: string | null;
  preview_data: Record<string, unknown> | null;
  error_message: string | null;
}

export interface SourceCreate {
  source_type: SourceType;
  asset_id?: string;
  url?: string;
  title?: string;
  description?: string;
  tags?: string[];
}

export interface EdgeCreate {
  source_id: string;
  target_id: string;
  kind: string;
}

export interface EdgeOut {
  id: string;
  user_id: string;
  source_id: string;
  target_id: string;
  kind: string;
  weight: number;
  metadata_: Record<string, unknown>;
  created_at: string;
  deleted_at: string | null;
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
