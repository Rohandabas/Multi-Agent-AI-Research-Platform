// TypeScript types that mirror the backend Pydantic schemas

export type Depth = 'quick' | 'standard' | 'deep';
export type ReportStatus = 'pending' | 'running' | 'complete' | 'error';

export interface ResearchConfig {
  depth: Depth;
  temperature: number;
  search_limit: number;
  pdf_limit: number;
  top_k: number;
  chunk_size: number;
  chunk_overlap: number;
  model: string;
  embedding_model: string;
  output_formats: string[];
  max_retries: number;
  timeout_seconds: number;
  sources: string[];
}

export interface ResearchRequest {
  query: string;
  config: Partial<ResearchConfig>;
}

export interface EvalMetrics {
  citation_coverage: number | null;
  faithfulness: number | null;
  hallucination_risk: number | null;
  retrieval_quality: number | null;
  completeness: number | null;
}

export interface Source {
  id: number;
  url: string;
  title: string;
  source_type: string;
  credibility_score: number;
  inline_ref: string;
}

export interface Report {
  id: string;
  job_id: string;
  query: string;
  status: ReportStatus;
  depth: Depth;
  report_markdown: string | null;
  pdf_path: string | null;
  docx_path: string | null;
  markdown_path: string | null;
  chart_paths: string[];
  total_tokens: number;
  total_cost_usd: number;
  duration_seconds: number | null;
  sources_used: Source[];
  eval_metrics: EvalMetrics | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface JobStartResponse {
  job_id: string;
  report_id: string;
  status: string;
  message: string;
  websocket_url: string;
}

// WebSocket event types
export type WsEventType =
  | 'connected'
  | 'agent_start'
  | 'agent_complete'
  | 'agent_error'
  | 'info'
  | 'report_ready'
  | 'pong';

export interface WsProgressEvent {
  event: WsEventType;
  agent?: string;
  message: string;
  progress: number;
  cost_so_far: number;
  timestamp: string;
  data?: Record<string, unknown>;
  state?: Record<string, unknown>;
}

export interface AgentStatus {
  name: string;
  displayName: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  startedAt?: string;
  completedAt?: string;
  message?: string;
}

// Agent display config
export const AGENTS: AgentStatus[] = [
  { name: 'PlannerAgent', displayName: 'Planner', status: 'pending' },
  { name: 'SearchAgent', displayName: 'Web Search', status: 'pending' },
  { name: 'PDFAgent', displayName: 'PDF Processing', status: 'pending' },
  { name: 'MemoryAgent', displayName: 'Memory Retrieval', status: 'pending' },
  { name: 'ExtractorAgent', displayName: 'Data Extraction', status: 'pending' },
  { name: 'FactCheckerAgent', displayName: 'Fact Checking', status: 'pending' },
  { name: 'WriterAgent', displayName: 'Report Writing', status: 'pending' },
  { name: 'ChartGeneratorAgent', displayName: 'Chart Generation', status: 'pending' },
  { name: 'ExporterAgent', displayName: 'Export', status: 'pending' },
  { name: 'EvaluatorAgent', displayName: 'Quality Evaluation', status: 'pending' },
];

export const DEFAULT_CONFIG: ResearchConfig = {
  depth: 'standard',
  temperature: 0.3,
  search_limit: 10,
  pdf_limit: 3,
  top_k: 10,
  chunk_size: 1000,
  chunk_overlap: 200,
  model: 'gemini-2.0-flash',
  embedding_model: 'models/text-embedding-004',
  output_formats: ['pdf', 'docx', 'markdown'],
  max_retries: 3,
  timeout_seconds: 60,
  sources: ['web', 'pdfs', 'memory'],
};
