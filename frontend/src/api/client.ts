import type {
  AnalysisRunStatus,
  CyclesData,
  DependencyGraph,
  ExplainResponse,
  GitHistoryData,
  HotspotsData,
  ImpactAnalysis,
  Repository,
  RepositoryCreate,
  RepositoryOverview,
  ViolationsData,
} from '../types';

const API_BASE = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Repositories
  async getRepositories(): Promise<Repository[]> {
    const res = await fetch(`${API_BASE}/repositories`);
    return handleResponse<Repository[]>(res);
  },

  async registerRepository(data: RepositoryCreate): Promise<Repository> {
    const res = await fetch(`${API_BASE}/repositories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<Repository>(res);
  },

  async deleteRepository(repoId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error(`Failed to delete repository: HTTP ${res.status}`);
    }
  },

  async getRepositoryStatus(repoId: string): Promise<AnalysisRunStatus> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/status`);
    return handleResponse<AnalysisRunStatus>(res);
  },

  async triggerAnalysis(repoId: string, branch?: string, forceFresh = false): Promise<any> {
    const res = await fetch(`${API_BASE}/repositories/${repoId}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ branch, force_fresh: forceFresh }),
    });
    return handleResponse<any>(res);
  },

  // Analysis Runs
  async getRunOverview(runId: string): Promise<RepositoryOverview> {
    const res = await fetch(`${API_BASE}/runs/${runId}/overview`);
    return handleResponse<RepositoryOverview>(res);
  },

  async getRunGraph(runId: string, nodeType?: string, limit = 500): Promise<DependencyGraph> {
    const params = new URLSearchParams();
    if (nodeType) params.append('node_type', nodeType);
    params.append('limit', limit.toString());
    const res = await fetch(`${API_BASE}/runs/${runId}/graph?${params.toString()}`);
    return handleResponse<DependencyGraph>(res);
  },

  async getRunCycles(runId: string): Promise<CyclesData> {
    const res = await fetch(`${API_BASE}/runs/${runId}/cycles`);
    return handleResponse<CyclesData>(res);
  },

  async getRunHotspots(runId: string): Promise<HotspotsData> {
    const res = await fetch(`${API_BASE}/runs/${runId}/hotspots`);
    return handleResponse<HotspotsData>(res);
  },

  async getRunViolations(runId: string): Promise<ViolationsData> {
    const res = await fetch(`${API_BASE}/runs/${runId}/violations`);
    return handleResponse<ViolationsData>(res);
  },

  async getRunCommits(runId: string): Promise<GitHistoryData> {
    const res = await fetch(`${API_BASE}/runs/${runId}/commits`);
    return handleResponse<GitHistoryData>(res);
  },

  async getRunImpact(runId: string, target: string): Promise<ImpactAnalysis> {
    const params = new URLSearchParams({ target });
    const res = await fetch(`${API_BASE}/runs/${runId}/impact?${params.toString()}`);
    return handleResponse<ImpactAnalysis>(res);
  },

  // AI Explanations
  async getAIExplanation(runId: string, filePath: string, question: string): Promise<ExplainResponse> {
    const res = await fetch(`${API_BASE}/ai/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        run_id: runId,
        file_path: filePath,
        question,
      }),
    });
    return handleResponse<ExplainResponse>(res);
  },

  // Architecture Diff
  async compareArchitecture(baseCommit = 'HEAD~1', targetCommit = 'HEAD'): Promise<any> {
    const res = await fetch(`${API_BASE}/diff`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        base_commit: baseCommit,
        target_commit: targetCommit,
      }),
    });
    return handleResponse<any>(res);
  },
};
