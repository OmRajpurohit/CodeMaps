import React, { useState } from 'react';
import {
  Sparkles,
  X,
  Send,
  Loader2,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../api/client';
import type { ExplainResponse } from '../types';

interface AIModalProps {
  isOpen: boolean;
  onClose: () => void;
  runId: string | null;
  initialFilePath?: string;
  initialQuestion?: string;
}

export const AIModal: React.FC<AIModalProps> = ({
  isOpen,
  onClose,
  runId,
  initialFilePath = '',
  initialQuestion = 'Why is this module risky and what are the architectural concerns?',
}) => {
  const [filePath, setFilePath] = useState(initialFilePath);
  const [question, setQuestion] = useState(initialQuestion);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAsk = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!runId || !filePath.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getAIExplanation(runId, filePath.trim(), question.trim());
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to generate AI explanation.');
    } finally {
      setIsLoading(false);
    }
  };

  const presetQuestions = [
    'Why is this module risky and what are the architectural concerns?',
    'How should we refactor to decouple this file from dependents?',
    'What is the blast radius risk if we modify this component?',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Evidence-Grounded AI Explainer</h3>
              <p className="text-xs text-slate-400">
                Factual reasoning grounded strictly in the deterministic code knowledge graph and Git dossier.
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

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Query Form */}
          <form onSubmit={handleAsk} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Target File Path:
              </label>
              <input
                type="text"
                placeholder="e.g. backend/app/main.py or src/index.ts"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                className="w-full px-3.5 py-2 text-xs font-mono rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Question / Prompt:
              </label>
              <textarea
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                required
              />
            </div>

            {/* Presets */}
            <div className="flex flex-wrap gap-2">
              {presetQuestions.map((q, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setQuestion(q)}
                  className="px-2.5 py-1 text-[11px] rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>

            <button
              type="submit"
              disabled={isLoading || !filePath.trim() || !runId}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors disabled:bg-slate-800 disabled:text-slate-500 shadow-md shadow-indigo-600/20"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Assembling Dossier & Analyzing...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Generate Factual Explanation</span>
                </>
              )}
            </button>
          </form>

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
              {error}
            </div>
          )}

          {/* AI Result */}
          {result && (
            <div className="space-y-6 pt-4 border-t border-slate-800">
              {/* Explanation Card */}
              <div className="p-5 rounded-xl border border-indigo-500/30 bg-indigo-500/5 backdrop-blur-sm space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-400">
                  <Sparkles className="w-4 h-4" />
                  <span>AI Architecture Analysis</span>
                </div>
                <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed font-sans">
                  {result.explanation}
                </div>
              </div>

              {/* Factual Dossier Cards */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Verified Evidence Dossier (Zero Hallucination Grounding)
                  </h4>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  {/* Metrics */}
                  <div className="p-3.5 rounded-lg bg-slate-800/60 border border-slate-750">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Static Metrics
                    </span>
                    <div className="space-y-1 font-mono text-slate-300 text-[11px]">
                      <div>LOC: {result.dossier.metrics.loc ?? 'N/A'}</div>
                      <div>Complexity: {result.dossier.metrics.cyclomatic_complexity ?? 'N/A'}</div>
                      <div>Fan-In: {result.dossier.metrics.fan_in ?? 0}</div>
                      <div>Fan-Out: {result.dossier.metrics.fan_out ?? 0}</div>
                    </div>
                  </div>

                  {/* Churn */}
                  <div className="p-3.5 rounded-lg bg-slate-800/60 border border-slate-750">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Git Churn
                    </span>
                    <div className="space-y-1 font-mono text-slate-300 text-[11px]">
                      <div>Commits: {result.dossier.churn.commit_count ?? 0}</div>
                      <div>Added: +{result.dossier.churn.lines_added ?? 0}</div>
                      <div>Deleted: -{result.dossier.churn.lines_deleted ?? 0}</div>
                      <div>Authors: {result.dossier.churn.author_count ?? 0}</div>
                    </div>
                  </div>

                  {/* Hotspots */}
                  <div className="p-3.5 rounded-lg bg-slate-800/60 border border-slate-750">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Hotspots ({result.dossier.hotspots.length})
                    </span>
                    <div className="space-y-1 text-slate-300 text-[11px]">
                      {result.dossier.hotspots.length === 0 ? (
                        <span className="text-slate-500 italic">No hotspot flag</span>
                      ) : (
                        result.dossier.hotspots.map((h, i) => (
                          <div key={i} className="font-mono text-amber-400">
                            Score: {h.score.toFixed(1)}
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Violations */}
                  <div className="p-3.5 rounded-lg bg-slate-800/60 border border-slate-750">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                      Violations ({result.dossier.violations.length})
                    </span>
                    <div className="space-y-1 text-slate-300 text-[11px]">
                      {result.dossier.violations.length === 0 ? (
                        <span className="text-emerald-400">Zero violations</span>
                      ) : (
                        result.dossier.violations.map((v, i) => (
                          <div key={i} className="truncate text-rose-400" title={v.rule_name}>
                            {v.rule_name}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
