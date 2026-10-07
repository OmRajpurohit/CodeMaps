import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Network,
  LayoutDashboard,
  RotateCcw,
  ShieldAlert,
  Flame,
  Zap,
  GitBranch,
  Loader2,
  AlertCircle,
} from 'lucide-react';

import { api } from './api/client';
import type {
  Repository,
  AnalysisRunStatus,
  RepositoryOverview,
  DependencyGraph,
  CyclesData,
  ViolationsData,
  HotspotsData,
  GitHistoryData,
  ImpactAnalysis,
} from './types';

import { Navbar } from './components/Navbar';
import { OverviewMetrics } from './components/OverviewMetrics';
import { GraphViewer } from './components/GraphViewer';
import { CyclesView } from './components/CyclesView';
import { ViolationsView } from './components/ViolationsView';
import { HotspotsView } from './components/HotspotsView';
import { ImpactView } from './components/ImpactView';
import { GitView } from './components/GitView';
import { AIModal } from './components/AIModal';
import { AddRepoModal } from './components/AddRepoModal';
import { DiffModal } from './components/DiffModal';

export const App: React.FC = () => {
  // Primary state
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [runStatus, setRunStatus] = useState<AnalysisRunStatus | null>(null);
  const [overview, setOverview] = useState<RepositoryOverview | null>(null);
  const [graphData, setGraphData] = useState<DependencyGraph | null>(null);
  const [cyclesData, setCyclesData] = useState<CyclesData | null>(null);
  const [violationsData, setViolationsData] = useState<ViolationsData | null>(null);
  const [hotspotsData, setHotspotsData] = useState<HotspotsData | null>(null);
  const [gitData, setGitData] = useState<GitHistoryData | null>(null);
  const [impactData, setImpactData] = useState<ImpactAnalysis | null>(null);

  // UI Navigation & Modals
  const [activeTab, setActiveTab] = useState<'graph' | 'overview' | 'cycles' | 'violations' | 'hotspots' | 'impact' | 'git'>('graph');
  const [isAddRepoOpen, setIsAddRepoOpen] = useState(false);
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [aiTargetFile, setAiTargetFile] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');

  // Loading flags
  const [isLoadingRepos, setIsLoadingRepos] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLoadingImpact, setIsLoadingImpact] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const pollingTimerRef = useRef<number | null>(null);

  // 1. Load initial repositories
  const fetchRepositories = useCallback(async () => {
    try {
      setErrorMessage(null);
      const repos = await api.getRepositories();
      setRepositories(repos);
      if (repos.length > 0 && !selectedRepo) {
        setSelectedRepo(repos[0]);
      }
    } catch (err: any) {
      setErrorMessage(`Failed to load repositories: ${err.message}`);
    } finally {
      setIsLoadingRepos(false);
    }
  }, [selectedRepo]);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  // 2. Fetch analysis run data when a repository is selected
  const fetchRunData = useCallback(async (runId: string) => {
    try {
      const [ov, gr, cy, vio, hot, git] = await Promise.allSettled([
        api.getRunOverview(runId),
        api.getRunGraph(runId),
        api.getRunCycles(runId),
        api.getRunViolations(runId),
        api.getRunHotspots(runId),
        api.getRunCommits(runId),
      ]);

      if (ov.status === 'fulfilled') setOverview(ov.value);
      if (gr.status === 'fulfilled') setGraphData(gr.value);
      if (cy.status === 'fulfilled') setCyclesData(cy.value);
      if (vio.status === 'fulfilled') setViolationsData(vio.value);
      if (hot.status === 'fulfilled') setHotspotsData(hot.value);
      if (git.status === 'fulfilled') setGitData(git.value);
    } catch (err: any) {
      console.error('Error fetching run data:', err);
    }
  }, []);

  // 3. Check status of current repo
  const checkRepoStatus = useCallback(async () => {
    if (!selectedRepo) return;
    try {
      const st = await api.getRepositoryStatus(selectedRepo.id);
      setRunStatus(st);

      if (['QUEUED', 'CLONING', 'SCANNING', 'PARSING', 'GRAPH_BUILDING', 'GIT_ANALYZING', 'EVALUATING_RULES', 'PERSISTING'].includes(st.status)) {
        setIsAnalyzing(true);
      } else {
        setIsAnalyzing(false);
      }

      if (st.status === 'COMPLETED' && st.run_id) {
        await fetchRunData(st.run_id);
      }
    } catch (err: any) {
      console.error('Error checking status:', err);
    }
  }, [selectedRepo, fetchRunData]);

  useEffect(() => {
    if (selectedRepo) {
      checkRepoStatus();
    }
  }, [selectedRepo, checkRepoStatus]);

  // 4. Polling effect while analysis is running
  useEffect(() => {
    if (isAnalyzing && selectedRepo) {
      pollingTimerRef.current = window.setInterval(() => {
        checkRepoStatus();
      }, 2500);
    } else if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [isAnalyzing, selectedRepo, checkRepoStatus]);

  // 5. Trigger Analysis
  const handleTriggerAnalysis = async () => {
    if (!selectedRepo || isAnalyzing) return;
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      await api.triggerAnalysis(selectedRepo.id, selectedRepo.default_branch);
      await checkRepoStatus();
    } catch (err: any) {
      setIsAnalyzing(false);
      setErrorMessage(`Failed to start analysis: ${err.message}`);
    }
  };

  // 6. Delete repository
  const handleDeleteRepo = async (repoId: string) => {
    try {
      await api.deleteRepository(repoId);
      const remaining = repositories.filter((r) => r.id !== repoId);
      setRepositories(remaining);
      setSelectedRepo(remaining.length > 0 ? remaining[0] : null);
      setOverview(null);
      setGraphData(null);
      setCyclesData(null);
      setViolationsData(null);
      setHotspotsData(null);
      setGitData(null);
      setImpactData(null);
    } catch (err: any) {
      setErrorMessage(`Failed to delete repository: ${err.message}`);
    }
  };

  // 7. Calculate blast radius impact
  const handleCalculateImpact = async (target: string) => {
    if (!runStatus?.run_id) return;
    setIsLoadingImpact(true);
    try {
      const imp = await api.getRunImpact(runStatus.run_id, target);
      setImpactData(imp);
      setActiveTab('impact');
    } catch (err: any) {
      setErrorMessage(`Failed to calculate blast radius: ${err.message}`);
    } finally {
      setIsLoadingImpact(false);
    }
  };

  // 8. Open AI modal with file
  const handleExplainNode = (filePath: string, question?: string) => {
    setAiTargetFile(filePath);
    if (question) setAiQuestion(question);
    setIsAIModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* Top Navigation */}
      <Navbar
        repositories={repositories}
        selectedRepo={selectedRepo}
        onSelectRepo={(r) => {
          setSelectedRepo(r);
          setOverview(null);
          setGraphData(null);
          setCyclesData(null);
          setViolationsData(null);
          setHotspotsData(null);
          setGitData(null);
          setImpactData(null);
        }}
        runStatus={runStatus}
        overview={overview}
        onTriggerAnalysis={handleTriggerAnalysis}
        onOpenAddRepo={() => setIsAddRepoOpen(true)}
        onOpenDiff={() => setIsDiffModalOpen(true)}
        onOpenAI={() => handleExplainNode(overview?.name || 'app/main.py')}
        onDeleteRepo={handleDeleteRepo}
        isAnalyzing={isAnalyzing}
        onRefresh={() => checkRepoStatus()}
      />

      {/* Error banner */}
      {errorMessage && (
        <div className="mx-6 mt-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-slate-400 hover:text-white text-xs font-semibold px-2 py-0.5 rounded"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 px-6 py-6 max-w-7xl w-full mx-auto space-y-6">
        {/* If no repositories */}
        {repositories.length === 0 && !isLoadingRepos && (
          <div className="p-16 text-center bg-slate-900/40 rounded-3xl border border-slate-800 backdrop-blur-md max-w-xl mx-auto my-12">
            <div className="p-4 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 inline-flex mb-4">
              <Network className="w-10 h-10" />
            </div>
            <h2 className="text-xl font-bold text-white">No Repositories Tracked</h2>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Register a public GitHub repository, private Git project, or local folder to construct multi-layered code knowledge graphs, analyze cycles, and detect architectural hotspots.
            </p>
            <button
              onClick={() => setIsAddRepoOpen(true)}
              className="mt-6 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/25 transition-all"
            >
              + Register First Repository
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        {selectedRepo && (
          <div className="flex items-center gap-1.5 border-b border-slate-800 pb-px overflow-x-auto">
            <button
              onClick={() => setActiveTab('graph')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'graph'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Network className="w-4 h-4" />
              <span>Architecture Graph</span>
              {graphData && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-400 font-mono">
                  {graphData.nodes.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('overview')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'overview'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Overview & Health</span>
            </button>

            <button
              onClick={() => setActiveTab('cycles')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'cycles'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <RotateCcw className="w-4 h-4" />
              <span>Cycles & SCCs</span>
              {cyclesData && cyclesData.total_cycles > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500/20 text-rose-300 font-mono">
                  {cyclesData.total_cycles}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('violations')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'violations'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Layer Violations</span>
              {violationsData && violationsData.total_violations > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500/20 text-amber-300 font-mono">
                  {violationsData.total_violations}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('hotspots')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'hotspots'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Flame className="w-4 h-4" />
              <span>Hotspots</span>
              {hotspotsData && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-orange-500/20 text-orange-300 font-mono">
                  {hotspotsData.total_hotspots}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('impact')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'impact'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="w-4 h-4" />
              <span>Blast Radius</span>
            </button>

            <button
              onClick={() => setActiveTab('git')}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
                activeTab === 'git'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitBranch className="w-4 h-4" />
              <span>Git & Churn</span>
            </button>
          </div>
        )}

        {/* Tab Views */}
        {selectedRepo && (
          <div>
            {activeTab === 'graph' && (
              <div>
                {graphData ? (
                  <GraphViewer
                    graphData={graphData}
                    cyclesData={cyclesData}
                    onSelectImpactNode={(nodeId) => handleCalculateImpact(nodeId)}
                    onExplainNode={(filePath) => handleExplainNode(filePath)}
                  />
                ) : (
                  <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400">
                    {isAnalyzing ? (
                      <div className="flex flex-col items-center gap-3">
                        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                        <span className="text-sm font-medium">Building code knowledge graph...</span>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm">No analysis run available yet for this repository.</p>
                        <button
                          onClick={handleTriggerAnalysis}
                          className="mt-4 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
                        >
                          Run Analysis Now
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'overview' && overview && (
              <OverviewMetrics overview={overview} onNavigateTab={(tab) => setActiveTab(tab as any)} />
            )}

            {activeTab === 'cycles' && (
              <CyclesView
                cyclesData={cyclesData}
                onSelectNodeInGraph={(_nodeName) => {
                  setActiveTab('graph');
                }}
              />
            )}

            {activeTab === 'violations' && (
              <ViolationsView
                violationsData={violationsData}
                onExplainViolation={(fp, msg) => handleExplainNode(fp, `Explain this violation: ${msg}`)}
              />
            )}

            {activeTab === 'hotspots' && (
              <HotspotsView
                hotspotsData={hotspotsData}
                onSelectImpactNode={(fp) => handleCalculateImpact(fp)}
                onExplainNode={(fp) => handleExplainNode(fp)}
              />
            )}

            {activeTab === 'impact' && (
              <ImpactView
                impactData={impactData}
                graphNodes={graphData?.nodes || []}
                onCalculateImpact={handleCalculateImpact}
                isLoading={isLoadingImpact}
              />
            )}

            {activeTab === 'git' && <GitView gitData={gitData} />}
          </div>
        )}
      </main>

      {/* Modals */}
      <AddRepoModal
        isOpen={isAddRepoOpen}
        onClose={() => setIsAddRepoOpen(false)}
        onRepoAdded={(repo) => {
          setRepositories((prev) => [repo, ...prev]);
          setSelectedRepo(repo);
          handleTriggerAnalysis();
        }}
      />

      <AIModal
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
        runId={runStatus?.run_id || null}
        initialFilePath={aiTargetFile}
        initialQuestion={aiQuestion}
      />

      <DiffModal
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
      />
    </div>
  );
};

export default App;
