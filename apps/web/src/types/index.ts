export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export type ObjectKind =
  | "page"
  | "asset"
  | "note"
  | "bookmark"
  | "collection"
  | "source"
  | "chat"
  | "claim"
  | "task";

export interface ObjectOut {
  id: string;
  user_id: string;
  kind: ObjectKind;
  title: string;
  description: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  is_pinned: boolean;
  is_archived: boolean;
  ai_generated: boolean;
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

export type ChatProvider = "auto" | "chatgpt" | "claude" | "markdown" | "plain_text" | "unknown";
export type ChatRawFormat = "json" | "md" | "txt";

export interface ChatTurnOut {
  turn_index: number;
  role: "user" | "assistant" | "system" | "tool" | "unknown" | string;
  author: string | null;
  content: string;
  created_at: string | null;
  metadata: Record<string, unknown>;
}

export type StructuredConfidence = "low" | "medium" | "high";

export interface StructuredTurnItem {
  turn_refs: number[];
  confidence: StructuredConfidence;
}

export interface StructuredDecision extends StructuredTurnItem {
  decision: string;
  rationale: string | null;
}

export interface StructuredOpenQuestion extends StructuredTurnItem {
  question: string;
  status: string;
}

export interface StructuredActionItem extends StructuredTurnItem {
  task: string;
  owner: string | null;
  due_at: string | null;
}

export interface StructuredClaim extends StructuredTurnItem {
  claim: string;
  type: "fact" | "hypothesis" | "preference" | "decision_context" | "unknown";
}

export interface StructuredConcept extends StructuredTurnItem {
  name: string;
  type: "person" | "organization" | "product" | "technology" | "topic" | "project" | "unknown";
}

export interface StructuredSuggestedLink {
  target_object_id: string | null;
  target_title: string;
  edge_kind:
    | "related_to"
    | "mentions"
    | "supports"
    | "contradicts"
    | "belongs_to_project"
    | "created_from";
  rationale: string;
  confidence: StructuredConfidence;
}

export interface StructuredChatSummary {
  title: string;
  summary: string;
  date_range: { start: string | null; end: string | null };
  topics: string[];
  key_decisions: StructuredDecision[];
  open_questions: StructuredOpenQuestion[];
  action_items: StructuredActionItem[];
  claims: StructuredClaim[];
  concepts: StructuredConcept[];
  suggested_links: StructuredSuggestedLink[];
  warnings: string[];
}

export interface ChatOut {
  id: string;
  user_id: string;
  kind: "chat";
  title: string;
  description: string | null;
  tags: string[];
  is_pinned: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  provider: string;
  external_chat_id: string | null;
  source_filename: string | null;
  raw_storage_path: string;
  raw_format: string;
  turn_count: number;
  started_at: string | null;
  ended_at: string | null;
  imported_at: string;
  parsed_turns: ChatTurnOut[];
  content_text: string;
  metadata: Record<string, unknown>;
  structured_summary: StructuredChatSummary | null;
  structured_summary_status: "none" | "previewed" | "applied" | "failed" | string;
  structured_summary_agent_run_id: string | null;
  structured_summary_updated_at: string | null;
}

export interface ChatImportResponse {
  imported: ChatOut[];
  total: number;
}

export interface StructuredSummaryPreviewResponse {
  structured_summary: StructuredChatSummary;
  agent_run_id: string;
  status: "none" | "previewed" | "applied" | "failed";
}

export interface StructuredSummaryApplyResponse {
  chat: ChatOut;
  created_objects: ObjectOut[];
  reused_objects: ObjectOut[];
  edges: Array<Record<string, unknown>>;
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

export interface EdgeWithObjectsOut {
  id: string;
  kind: string;
  weight: number;
  source_id: string;
  target_id: string;
  source?: { id: string; kind: string; title: string } | null;
  target?: { id: string; kind: string; title: string } | null;
  source_object: { id: string; kind: string; title: string } | null;
  target_object: { id: string; kind: string; title: string } | null;
  created_at: string;
}

export interface RelatedObjectOut {
  id: string;
  kind: string;
  title: string;
  distance: number;
  edge_kind: string;
  direction: string;
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

export type SearchMode = "keyword" | "semantic" | "hybrid";

export interface SearchSnippet {
  text: string;
  highlights: [number, number][];
}

export interface SearchResult {
  id: string;
  kind: ObjectKind | string;
  title: string;
  snippet: SearchSnippet | null;
  tags: string[];
  score: number;
  updated_at: string;
  source_type: string | null;
  ingestion_status: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
  mode: string;
}

export interface HybridSearchResult extends SearchResult {
  keyword_score: number;
  vector_score: number;
  recency_boost: number;
}

export interface HybridSearchResponse {
  results: HybridSearchResult[];
  total: number;
  query: string;
  mode: string;
  embeddings_used: boolean;
}

// ── AI feature types ──────────────────────────────────────────────────────────

export interface SummarizeResponse {
  summary: string;
  agent_run_id: string;
  cached: boolean;
}

export interface ExtractedItem {
  id: string;
  title: string;
}

export interface ExtractResponse {
  items: ExtractedItem[];
  agent_run_id: string;
}

export interface LinkSuggestion {
  target_id: string;
  target_title: string;
  target_kind: string;
  reason: string;
  confidence: number;
}

export interface SuggestLinksResponse {
  suggestions: LinkSuggestion[];
  agent_run_id: string;
}

export interface AiCitation {
  object_id: string;
  title: string;
  kind: string;
  snippet: string | null;
}

export interface AnswerResponse {
  answer: string;
  citations: AiCitation[];
  agent_run_id: string;
  context_count: number;
}

export interface TriageResponse {
  suggested_tags: string[];
  suggested_title: string | null;
  summary: string;
  agent_run_id: string;
}
