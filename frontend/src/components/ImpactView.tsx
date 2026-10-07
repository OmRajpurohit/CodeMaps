import React, { useState } from 'react';
import {
  Zap,
  Target,
} from 'lucide-react';
import type { ImpactAnalysis, GraphNode } from '../types';

interface ImpactViewProps {
  impactData: ImpactAnalysis | null;
  graphNodes: GraphNode[];
  onCalculateImpact: (target: string) => void;
  isLoading: boolean;
}

export const ImpactView: React.FC<ImpactViewProps> = ({
  impactData,
  graphNodes,
  onCalculateImpact,
  isLoading,
}) => {
  const [targetInput, setTargetInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetInput.trim()) {
      onCalculateImpact(targetInput.trim());
    }
  };

  const getImpactMeta = (score: number) => {
    if (score >= 70) {
      return {
        label: 'Critical Blast Radius',
        color: 'text-rose-400',
        bgColor: 'bg-rose-500/10',
        borderColor: 'border-rose-500/30',
        desc: 'Wide ripple effect across the entire repository. Breaking changes will cascade through numerous modules.',
      };
    }
    if (score >= 30) {
      return {
        label: 'Moderate Impact',
        color: 'text-amber-400',
        bgColor: 'bg-amber-500/10',
        borderColor: 'border-amber-500/30',
        desc: 'Noticeable downstream ripple effect. Several dependent modules will require corresponding test updates.',
      };
    }
    return {
      label: 'Contained Blast Radius',
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/30',
      desc: 'Localized changes with low blast radius. Safe to modify with minimal regression risk.',
    };
  };

  return (
    <div className="space-y-6">
      {/* Target Selector Toolbar */}
      <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Target className="w-4 h-4 text-indigo-400" />
            <span>Select Target File or Symbol:</span>
          </div>

          <div className="relative flex-1 min-w-[280px]">
            <input
              type="text"
              placeholder="e.g. app.py, models.py, file:src/index.ts"
              value={targetInput}
              onChange={(e) => setTargetInput(e.target.value)}
              list="nodes-datalist"
              className="w-full px-3 py-2 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <datalist id="nodes-datalist">
              {graphNodes.slice(0, 100).map((n) => (
                <option key={n.id} value={n.file_path || n.name}>
                  {n.qualified_name} ({n.node_type})
                </option>
              ))}
            </datalist>
          </div>

          <button
            type="submit"
            disabled={isLoading || !targetInput.trim()}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:bg-slate-800 disabled:text-slate-500"
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>{isLoading ? 'Traversing...' : 'Analyze Blast Radius'}</span>
          </button>
        </form>
      </div>

      {/* Results View */}
      {impactData ? (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Blast Score Card */}
            {(() => {
              const meta = getImpactMeta(impactData.impact_score);
              return (
                <div className={`p-6 rounded-2xl border ${meta.borderColor} ${meta.bgColor} backdrop-blur-sm`}>
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Blast Radius Risk Score
                  </span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className={`text-5xl font-black ${meta.color}`}>
                      {impactData.impact_score.toFixed(0)}
                    </span>
                    <span className="text-xl font-medium text-slate-400">/ 100</span>
                  </div>
                  <p className={`text-xs font-semibold mt-1 ${meta.color}`}>{meta.label}</p>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">{meta.desc}</p>
                </div>
              );
            })()}

            {/* Dependents Count Card */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Target Entity
                </span>
                <p className="text-base font-bold text-white mt-1 break-all">
                  {impactData.target_name}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                <div>
                  <span className="text-[11px] text-slate-400 uppercase font-medium">Direct</span>
                  <p className="text-2xl font-bold text-sky-400 mt-0.5">
                    {impactData.direct_dependents_count}
                  </p>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 uppercase font-medium">Transitive</span>
                  <p className="text-2xl font-bold text-indigo-400 mt-0.5">
                    {impactData.transitive_dependents_count}
                  </p>
                </div>
              </div>
            </div>

            {/* Total Affected Card */}
            <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Total Downstream Reach
                </span>
                <p className="text-4xl font-extrabold text-white mt-2">
                  {impactData.affected_nodes.length}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Unique modules and symbols affected by changes to this node.
                </p>
              </div>

              <div className="text-xs text-slate-500 pt-3 border-t border-slate-800 font-mono">
                Reverse graph traversal depth: {impactData.dependency_chain.length > 0 ? impactData.dependency_chain[0].length - 1 : 0}
              </div>
            </div>
          </div>

          {/* Affected Nodes Table */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden">
            <div className="p-4 border-b border-slate-800">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Downstream Affected Entities ({impactData.affected_nodes.length})
              </h4>
            </div>

            {impactData.affected_nodes.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs italic">
                No downstream dependents found. This module is an independent leaf in the dependency graph.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-800/40 text-slate-400 uppercase text-[11px] font-semibold">
                      <th className="py-3 px-4">Entity</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Depth</th>
                      <th className="py-3 px-4">Relation</th>
                      <th className="py-3 px-4">Impact Weight</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {impactData.affected_nodes.map((node, idx) => (
                      <tr key={idx} className="hover:bg-slate-850/60 transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-slate-200">
                          {node.name}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[11px] font-mono">
                            {node.node_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          Level {node.depth}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                              node.is_direct
                                ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                                : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                            }`}
                          >
                            {node.is_direct ? 'Direct Dependent' : 'Transitive'}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400">
                          {node.impact_weight.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 max-w-xl mx-auto my-8">
          <div className="p-4 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 inline-flex mb-3">
            <Zap className="w-8 h-8" />
          </div>
          <h4 className="text-base font-bold text-white">Perform Blast Radius Analysis</h4>
          <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
            Enter a target file or symbol name above (or click "Calculate Blast Radius" from the graph inspector) to simulate code changes and compute the exact downstream impact tree.
          </p>
        </div>
      )}
    </div>
  );
};
