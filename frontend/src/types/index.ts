export interface Repository {
  id: string;
  url: string;
  name: string;
  default_branch: string;
  description?: string | null;
  primary_language?: string | null;
  stars: number;
  forks: number;
  created_at: string;
  updated_at: string;
}

export interface RepositoryCreate {
  url: string;
  name?: string;
  default_branch?: string;
}

export interface AnalysisRunStatus {
  run_id: string | null;
  status: 'NOT_ANALYZED' | 'QUEUED' | 'CLONING' | 'SCANNING' | 'PARSING' | 'GRAPH_BUILDING' | 'GIT_ANALYZING' | 'EVALUATING_RULES' | 'PERSISTING' | 'COMPLETED' | 'FAILED';
  commit_sha?: string | null;
  error_message?: string | null;
  summary_stats?: Record<string, any> | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface RepositoryOverview {
  repository_id: string;
  name: string;
  url: string;
  commit_sha: string;
  status: string;
  total_files: number;
  total_symbols: number;
  total_loc: number;
  primary_language: string | null;
  languages_breakdown: Record<string, number>;
  health_score: number;
  total_cycles: number;
  total_violations: number;
  total_hotspots: number;
}

export interface GraphNode {
  id: string;
  name: string;
  qualified_name: string;
  node_type: string; // 'file' | 'class' | 'function' | 'method' | 'package'
  file_path?: string | null;
  loc?: number | null;
  complexity?: number | null;
  fan_in: number;
  fan_out: number;
  instability: number;
  degree_centrality: number;
  metadata?: Record<string, any>;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  edge_type: string; // 'imports' | 'calls' | 'inherits' | 'implements' | 'contains'
  line_number?: number | null;
  properties?: Record<string, any>;
}

export interface DependencyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
}

export interface CyclePath {
  length: number;
  nodes: string[];
  description: string;
}

export interface StronglyConnectedComponent {
  size: number;
  nodes: string[];
}

export interface CyclesData {
  total_cycles: number;
  cycles: CyclePath[];
  scc_clusters: StronglyConnectedComponent[];
}

export interface Hotspot {
  id: string;
  file_id?: string | null;
  file_path: string;
  score: number;
  churn_score: number;
  centrality_score: number;
  complexity_score: number;
  rationale: string;
  created_at: string;
}

export interface HotspotsData {
  total_hotspots: number;
  hotspots: Hotspot[];
}

export interface Violation {
  id: string;
  source_file_path: string;
  target_file_path: string;
  rule_name: string;
  severity: 'error' | 'warning' | string;
  message: string;
  layer_from?: string | null;
  layer_to?: string | null;
  created_at: string;
}

export interface ViolationsData {
  total_violations: number;
  violations: Violation[];
}

export interface ImpactNode {
  node_id: string;
  name: string;
  node_type: string;
  depth: number;
  impact_weight: number;
  is_direct: boolean;
  is_test_file: boolean;
}

export interface ImpactAnalysis {
  target_node_id: string;
  target_name: string;
  impact_score: number;
  direct_dependents_count: number;
  transitive_dependents_count: number;
  affected_nodes: ImpactNode[];
  dependency_chain: string[][];
}

export interface GitCommit {
  id: string;
  commit_sha: string;
  author_alias: string;
  authored_at: string;
  message: string;
  insertions: number;
  deletions: number;
  files_changed: number;
}

export interface GitFileChurn {
  id: string;
  file_path: string;
  commit_count: number;
  lines_added: number;
  lines_deleted: number;
  author_count: number;
  ownership_entropy: number;
}

export interface GitHistoryData {
  commits: GitCommit[];
  file_churns: GitFileChurn[];
}

export interface ExplainResponse {
  file_path: string;
  explanation: string;
  dossier: {
    run_id: string;
    file_path: string;
    metrics: Record<string, any>;
    hotspots: Array<{ score: number; rationale: string }>;
    violations: Array<{ rule_name: string; severity: string; message: string; source: string; target: string }>;
    churn: {
      commit_count?: number;
      lines_added?: number;
      lines_deleted?: number;
      author_count?: number;
    };
  };
}
