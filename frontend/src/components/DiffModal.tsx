import React, { useState } from 'react';
import { GitCompare, X, Loader2 } from 'lucide-react';
import { api } from '../api/client';

interface DiffModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DiffModal: React.FC<DiffModalProps> = ({ isOpen, onClose }) => {
  const [baseCommit, setBaseCommit] = useState('HEAD~1');
  const [targetCommit, setTargetCommit] = useState('HEAD');
  const [isLoading, setIsLoading] = useState(false);
  const [diffResult, setDiffResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDiff = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.compareArchitecture(baseCommit, targetCommit);
      setDiffResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to compare commits.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              <GitCompare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Architecture Diff</h3>
              <p className="text-xs text-slate-400">
                Compare structural dependency graphs between two Git revisions or branches.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto max-h-[80vh]">
          <form onSubmit={handleDiff} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Base Commit / Branch:
                </label>
                <input
                  type="text"
                  placeholder="HEAD~1 or main"
                  value={baseCommit}
                  onChange={(e) => setBaseCommit(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs font-mono rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Target Commit / Branch:
                </label>
                <input
                  type="text"
                  placeholder="HEAD or feature-branch"
                  value={targetCommit}
                  onChange={(e) => setTargetCommit(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs font-mono rounded-lg bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs transition-colors disabled:bg-slate-800 shadow-md shadow-cyan-600/20"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Computing Graph Delta...</span>
                </>
              ) : (
                <>
                  <GitCompare className="w-3.5 h-3.5" />
                  <span>Compute Architecture Delta</span>
                </>
              )}
            </button>
          </form>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
              {error}
            </div>
          )}

          {diffResult && (
            <div className="space-y-4 pt-4 border-t border-slate-800">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">
                    Added Edges
                  </span>
                  <p className="text-xl font-bold text-emerald-400 mt-1">
                    +{diffResult.added_edges?.length ?? 0}
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">
                    Removed Edges
                  </span>
                  <p className="text-xl font-bold text-rose-400 mt-1">
                    -{diffResult.removed_edges?.length ?? 0}
                  </p>
                </div>
                <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">
                    New Cycles
                  </span>
                  <p className="text-xl font-bold text-amber-400 mt-1">
                    {diffResult.new_cycles?.length ?? 0}
                  </p>
                </div>
              </div>

              {diffResult.risk_summary && (
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 text-xs text-slate-300">
                  <span className="font-bold text-white block mb-1">Risk Summary:</span>
                  {diffResult.risk_summary}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
