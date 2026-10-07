import React from 'react';
import {
  RotateCcw,
  CheckCircle2,
  ArrowRight,
  Layers,
  Lightbulb,
} from 'lucide-react';
import type { CyclesData } from '../types';

interface CyclesViewProps {
  cyclesData: CyclesData | null;
  onSelectNodeInGraph: (nodeId: string) => void;
}

export const CyclesView: React.FC<CyclesViewProps> = ({ cyclesData, onSelectNodeInGraph }) => {
  if (!cyclesData) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/50 rounded-2xl border border-slate-800">
        Loading cycle analysis...
      </div>
    );
  }

  const { total_cycles, cycles, scc_clusters } = cyclesData;

  if (total_cycles === 0) {
    return (
      <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 backdrop-blur-sm max-w-2xl mx-auto my-8">
        <div className="inline-flex p-4 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <h3 className="text-xl font-bold text-white">No Circular Dependencies Detected</h3>
        <p className="text-sm text-slate-400 mt-2 leading-relaxed">
          The dependency graph forms a clean Directed Acyclic Graph (DAG). There are no mutual or recursive dependencies between modules, guaranteeing safe modular builds and clean separation of concerns.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="p-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 backdrop-blur-sm flex items-start gap-4">
        <div className="p-3 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30 shrink-0">
          <RotateCcw className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-white">
              {total_cycles} Circular {total_cycles === 1 ? 'Dependency' : 'Dependencies'} Detected
            </h3>
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
              Severity: High
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Tarjan's strongly connected components algorithm identified circular dependency chains. Circular coupling leads to tight runtime interdependence, initialization race conditions, and prevents independent unit testing.
          </p>
        </div>
      </div>

      {/* Cycles List */}
      <div className="space-y-4">
        <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Detected Cycle Paths ({cycles.length})
        </h4>

        <div className="grid grid-cols-1 gap-4">
          {cycles.map((c, idx) => (
            <div
              key={idx}
              className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-rose-500/40 transition-colors backdrop-blur-sm"
            >
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-rose-500/20 text-rose-400 font-mono text-xs font-bold">
                    #{idx + 1}
                  </span>
                  <span className="text-xs font-semibold text-slate-300">
                    Cycle Length: {c.length} Modules
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-500">{c.description}</span>
              </div>

              {/* Cycle Chain Path */}
              <div className="flex flex-wrap items-center gap-2 py-4">
                {c.nodes.map((nodeName, nIdx) => (
                  <React.Fragment key={nIdx}>
                    <button
                      onClick={() => onSelectNodeInGraph(nodeName)}
                      className="px-3 py-1.5 text-xs font-mono font-medium rounded-lg bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-200 border border-slate-700 transition-colors cursor-pointer group flex items-center gap-1.5"
                    >
                      <span>{nodeName}</span>
                    </button>
                    {nIdx < c.nodes.length - 1 && (
                      <ArrowRight className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    )}
                  </React.Fragment>
                ))}
              </div>

              {/* Remediation hint */}
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300/90">
                <Lightbulb className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-amber-300">Decoupling Strategy: </span>
                  Break the cycle by extracting shared types/interfaces into a common abstraction module, or apply the Dependency Inversion Principle (DIP).
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Strongly Connected Components */}
      {scc_clusters.length > 0 && (
        <div className="space-y-4 pt-4">
          <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Strongly Connected Component (SCC) Clusters ({scc_clusters.length})</span>
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {scc_clusters.map((scc, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm"
              >
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
                  <span className="font-bold text-white">Cluster #{idx + 1}</span>
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
                    {scc.size} symbols
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 mt-3 max-h-36 overflow-y-auto">
                  {scc.nodes.map((node, nIdx) => (
                    <span
                      key={nIdx}
                      className="px-2 py-1 text-[11px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700 truncate max-w-full"
                    >
                      {node}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
