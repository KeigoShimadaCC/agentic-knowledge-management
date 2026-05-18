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
  | "task"
  | "project"
  | "resume_bullet_set"
  | "interview_story"
  | "ai_notification";

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

export interface WebCitation {
  title: string;
  url: string;
  snippet: string | null;
}

export interface AnswerRequest {
  q: string;
  kind?: string | null;
  limit?: number;
  object_ids?: string[] | null;
}

export interface AiAnswerResponse {
  answer: string;
  citations: AiCitation[];
  agent_run_id: string;
  context_count: number;
  web_citations: WebCitation[];
  warning: string | null;
}

export interface AnswerResponse extends AiAnswerResponse {}

export interface EnrichPageRequest {
  page_id: string;
  query: string;
}

export interface EnrichPageResponse {
  sources_created: string[];
  edges_created: string[];
  agent_run_id: string;
}

export interface TriageResponse {
  suggested_tags: string[];
  suggested_title: string | null;
  summary: string;
  agent_run_id: string;
}

// ── Workspace types ────────────────────────────────────────────────────────

export type WorkspaceSplitAPI = "horizontal" | "vertical";
export type PaneModeAPI = "read" | "edit";

export interface WorkspacePaneAPI {
  id: string;
  object_id: string | null;
  object_kind: string | null;
  size_pct: number;
  mode: PaneModeAPI;
}

export interface WorkspaceLayoutAPI {
  version: 1;
  split: WorkspaceSplitAPI | null;
  panes: WorkspacePaneAPI[];
  active_pane_id: string;
}

export interface WorkspaceOut {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  layout: WorkspaceLayoutAPI;
  is_pinned: boolean;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface WorkspaceCreate {
  name: string;
  description?: string | null;
  layout: WorkspaceLayoutAPI;
  is_pinned?: boolean;
}

export interface WorkspaceUpdate {
  name?: string;
  description?: string | null;
  layout?: WorkspaceLayoutAPI;
  is_pinned?: boolean;
}

// ── Career memory types ─────────────────────────────────────────────────────

export type ProjectStatus = "active" | "paused" | "completed" | "archived";
export type ProjectConfidence = "manual" | "ai_extracted" | "verified";

export interface ProjectOut {
  id: string;
  user_id: string;
  kind: "project";
  title: string;
  description: string | null;
  tags: string[];
  is_pinned: boolean;
  is_archived: boolean;
  period_start: string | null;
  period_end: string | null;
  role: string | null;
  organization: string | null;
  problem: string | null;
  actions: string | null;
  results: string | null;
  metrics: Record<string, string | number | boolean | null>;
  skills: string[];
  status: ProjectStatus;
  confidence: ProjectConfidence;
  extracted_from: string | null;
  extracted_by_agent_run_id: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ProjectCreate {
  title: string;
  description?: string;
  tags?: string[];
  period_start?: string;
  period_end?: string;
  role?: string;
  organization?: string;
  problem?: string;
  actions?: string;
  results?: string;
  metrics?: Record<string, string | number | boolean | null>;
  skills?: string[];
  status?: ProjectStatus;
  extracted_from?: string;
  confidence?: ProjectConfidence;
}

export interface ProjectUpdate extends Partial<ProjectCreate> {}

export interface ResumeBullet {
  text: string;
  evidence_object_ids: string[];
  confidence: "high" | "medium" | "low";
  metrics_cited: string[];
}

export interface StarStory {
  situation: string;
  task: string;
  action: string;
  result: string;
  evidence_object_ids: string[];
}

export interface ResumeBulletSetOut {
  id: string;
  user_id: string;
  project_id: string;
  target_role: string | null;
  emphasis: string | null;
  count: number;
  bullets: ResumeBullet[];
  agent_run_id: string | null;
  prompt_version: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface InterviewStoryOut {
  id: string;
  user_id: string;
  project_id: string;
  question_type: "behavioral" | "technical" | "leadership";
  target_role: string | null;
  max_words: number;
  word_count: number;
  story: StarStory;
  agent_run_id: string | null;
  prompt_version: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface SaveResumeBulletSetRequest {
  target_role?: string;
  emphasis?: string;
  count: number;
  bullets: ResumeBullet[];
  agent_run_id?: string;
  prompt_version?: string;
}

export interface SaveInterviewStoryRequest {
  question_type: "behavioral" | "technical" | "leadership";
  target_role?: string;
  max_words: number;
  word_count: number;
  story: StarStory;
  agent_run_id?: string;
  prompt_version?: string;
}

export interface GenerateResumeBulletsRequest {
  project_id: string;
  target_role?: string;
  emphasis?: string;
  count?: number;
  max_evidence_objects?: number;
}

export interface GenerateResumeBulletsResponse {
  project_id: string;
  bullets: ResumeBullet[];
  agent_run_id: string;
  evidence_count: number;
}

export interface GenerateInterviewStoryRequest {
  project_id: string;
  question_type?: "behavioral" | "technical" | "leadership";
  target_role?: string;
  max_words?: number;
  max_evidence_objects?: number;
}

export interface GenerateInterviewStoryResponse {
  project_id: string;
  story: StarStory;
  agent_run_id: string;
  word_count: number;
}

export interface ExtractProjectRequest {
  source_id: string;
  create?: boolean;
  period_hint?: [string | null, string | null];
}

export interface ExtractedProjectDraft {
  title: string;
  description: string | null;
  period_start: string | null;
  period_end: string | null;
  role: string | null;
  organization: string | null;
  problem: string | null;
  actions: string | null;
  results: string | null;
  metrics: Record<string, unknown>;
  skills: string[];
  confidence: number;
}

export interface ExtractProjectResponse {
  draft: ExtractedProjectDraft;
  project_id: string | null;
  agent_run_id: string;
  source_id: string;
}

// ── MCP Connections ───────────────────────────────────────────────────────────

export type McpTransport = "stdio" | "sse";

export interface McpToolDefinition {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface McpConnectionOut {
  id: string;
  name: string;
  transport: McpTransport;
  command: string | null;
  args: string[];
  url: string | null;
  env_vars: Record<string, string>;
  capabilities: McpToolDefinition[] | null;
  enabled: boolean;
  last_tested_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface McpConnectionCreate {
  name: string;
  transport: McpTransport;
  command?: string;
  args?: string[];
  url?: string;
  env_vars?: Record<string, string>;
  enabled?: boolean;
}

export interface McpConnectionUpdate {
  name?: string;
  command?: string;
  args?: string[];
  url?: string;
  env_vars?: Record<string, string>;
  enabled?: boolean;
}

export interface McpConnectionTestResult {
  ok: boolean;
  tools: McpToolDefinition[];
  error?: string;
}

export interface McpCallRequest {
  tool_name: string;
  args?: Record<string, unknown>;
}

export interface McpCallResponse {
  result: Record<string, unknown>;
  connection_name: string;
}

export interface McpIngestRequest {
  tool_name: string;
  args?: Record<string, unknown>;
  target_kind?: "page" | "source";
  tags?: string[];
}

export interface McpIngestResponse {
  job_id: string;
  status: string;
}

// ── Settings ─────────────────────────────────────────────────────────────────

export interface SecretStatus {
  key: "openai_api_key" | "anthropic_api_key";
  configured: boolean;
  source: "runtime" | "env" | "none";
  redacted: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  last_tested_at: string | null;
}

export interface AiFeatureSettingOut {
  feature_key: string;
  display_name: string;
  enabled: boolean;
  provider: string | null;
  model: string | null;
  temperature: number | null;
  max_tokens: number | null;
  effort: string | null;
  resolved_provider: string | null;
  resolved_model: string | null;
  resolved_temperature: number | null;
  resolved_max_tokens: number | null;
  supports_effort: boolean;
  note: string | null;
}

export interface AiFeatureSettingPatch {
  enabled?: boolean;
  provider?: "openai" | "anthropic" | null;
  model?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  effort?: string | null;
}

export interface PromptOut {
  key: string;
  display_name: string;
  default_template: string;
  effective_template: string;
  override_template: string | null;
  has_override: boolean;
  variables: string[];
  response_contract: string;
  updated_at: string | null;
}

export interface EnvExportStatus {
  available: boolean;
  path: string | null;
  last_warning: string | null;
  allowlisted_keys: string[];
}

export interface BackgroundAiSettings {
  enabled: boolean;
  tasks: string[];
}

export interface McpSettingsSummary {
  connection_count: number;
  enabled_count: number;
  web_search_threshold: number;
  web_search_connection_name: string | null;
}

export interface SettingsResponse {
  secrets: SecretStatus[];
  features: AiFeatureSettingOut[];
  prompts: PromptOut[];
  background_ai: BackgroundAiSettings;
  mcp: McpSettingsSummary;
  env_export: EnvExportStatus;
}

export interface SecretPatch {
  openai_api_key?: string | null;
  anthropic_api_key?: string | null;
  clear_openai_api_key?: boolean;
  clear_anthropic_api_key?: boolean;
  export_env?: boolean;
}

export interface ProviderTestOut {
  provider: "openai" | "anthropic";
  ok: boolean;
  status: string;
  error: string | null;
  tested_at: string;
}
