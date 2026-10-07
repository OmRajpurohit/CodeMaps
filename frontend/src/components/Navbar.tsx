import React from 'react';
import {
  Layers,
  Play,
  Plus,
  RefreshCw,
  Sparkles,
  GitCompare,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Trash2,
} from 'lucide-react';
import type { Repository, AnalysisRunStatus, RepositoryOverview } from '../types';

interface NavbarProps {
  repositories: Repository[];
  selectedRepo: Repository | null;
  onSelectRepo: (repo: Repository) => void;
  runStatus: AnalysisRunStatus | null;
  overview: RepositoryOverview | null;
  onTriggerAnalysis: () => void;
  onOpenAddRepo: () => void;
  onOpenDiff: () => void;
  onOpenAI: () => void;
  onDeleteRepo: (id: string) => void;
  isAnalyzing: boolean;
  onRefresh: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  repositories,
  selectedRepo,
  onSelectRepo,
  runStatus,
  overview,
  onTriggerAnalysis,
  onOpenAddRepo,
  onOpenDiff,
  onOpenAI,
  onDeleteRepo,
  isAnalyzing,
  onRefresh,
}) => {
  const getStatusBadge = () => {
    if (!runStatus) return null;

    if (isAnalyzing || ['QUEUED', 'CLONING', 'SCANNING', 'PARSING', 'GRAPH_BUILDING', 'GIT_ANALYZING', 'EVALUATING_RULES', 'PERSISTING'].includes(runStatus.status)) {
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          {runStatus.status.replace('_', ' ')}
        </span>
      );
    }

    if (runStatus.status === 'COMPLETED') {
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          ANALYZED
        </span>
      );
    }

    if (runStatus.status === 'FAILED') {
      return (
        <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <AlertCircle className="w-3.5 h-3.5" />
          FAILED
        </span>
      );
    }

    return (
      <span className="px-3 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-400 border border-slate-700">
        NOT ANALYZED
      </span>
    );
  };

  const getHealthBadge = () => {
    if (!overview) return null;
    const score = overview.health_score;
    const color =
      score >= 85
        ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
        : score >= 60
        ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
        : 'text-rose-400 border-rose-500/30 bg-rose-500/10';

    return (
      <div className={`flex items-center gap-1.5 px-3 py-1 text-xs font-bold rounded-lg border ${color}`}>
        <span>Health</span>
        <span className="text-sm">{score.toFixed(0)}%</span>
      </div>
    );
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="flex items-center justify-between px-6 py-3.5">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 shadow-lg shadow-indigo-500/20">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">CodeAtlas</span>
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v0.1
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Repository Intelligence & Architecture Graph
            </p>
          </div>
        </div>

        {/* Center: Repo Selector */}
        <div className="flex items-center gap-2.5 max-w-md w-full mx-4">
          <div className="relative flex-1">
            <select
              value={selectedRepo?.id || ''}
              onChange={(e) => {
                const found = repositories.find((r) => r.id === e.target.value);
                if (found) onSelectRepo(found);
              }}
              className="w-full pl-3 pr-8 py-1.5 text-xs font-medium rounded-lg bg-slate-900 border border-slate-700/80 text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer appearance-none truncate"
            >
              {repositories.length === 0 && <option value="">No repositories registered</option>}
              {repositories.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name} ({repo.default_branch})
                </option>
              ))}
            </select>
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-xs">
              ▼
            </div>
          </div>

          <button
            onClick={onOpenAddRepo}
            title="Register new repository"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5 text-indigo-400" />
            <span>Add Repo</span>
          </button>

          {selectedRepo && (
            <button
              onClick={() => {
                if (window.confirm(`Delete repository "${selectedRepo.name}" and all analysis runs?`)) {
                  onDeleteRepo(selectedRepo.id);
                }
              }}
              title="Delete repository"
              className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {getStatusBadge()}
          {getHealthBadge()}

          <button
            onClick={onTriggerAnalysis}
            disabled={!selectedRepo || isAnalyzing}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg shadow-sm transition-all ${
              isAnalyzing || !selectedRepo
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30 active:scale-95'
            }`}
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Analysis</span>
              </>
            )}
          </button>

          <button
            onClick={onOpenDiff}
            title="Architecture Diff"
            className="hidden md:flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors"
          >
            <GitCompare className="w-3.5 h-3.5 text-cyan-400" />
            <span>Diff</span>
          </button>

          <button
            onClick={onOpenAI}
            title="AI Evidence Explainer"
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 rounded-lg transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">AI Explainer</span>
          </button>

          <button
            onClick={onRefresh}
            title="Refresh data"
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
