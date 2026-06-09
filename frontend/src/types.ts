export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  kind?: "text" | "status" | "error";
}

export interface ArtifactInfo {
  name: string;
  url: string;
  kind: "image";
}

export interface EventCall {
  id?: string;
  name?: string;
  args?: Record<string, unknown>;
  response?: Record<string, unknown>;
}

export interface EventSummary {
  id: string;
  author: string;
  timestamp: number;
  text: string;
  function_calls: EventCall[];
  function_responses: EventCall[];
  artifact_delta: Record<string, number>;
  state_delta: Record<string, unknown>;
}

export interface DashboardState {
  session_id: string;
  turn_count: number;
  tool_count: number;
  tool_names: string[];
  tables: string[];
  artifact: ArtifactInfo | null;
  summary: string;
  last_updated: string;
}

export interface ChatResponse {
  status: "ok" | "error";
  session_id: string;
  user_id: string;
  assistant_message: string;
  dashboard: DashboardState;
  events: EventSummary[];
  artifacts: ArtifactInfo[];
  error?: string | null;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
}

export interface HealthResponse {
  status: string;
  auth_mode: string;
  api_key_state: string;
  databricks_host: string;
  session_db: string;
  charts_dir: string;
  vertex_project?: string | null;
  vertex_location?: string | null;
}
