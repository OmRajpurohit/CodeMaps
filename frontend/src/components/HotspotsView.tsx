import React, { useState } from 'react';
import {
  Flame,
  Zap,
  Sparkles,
  Search,
} from 'lucide-react';
import type { HotspotsData } from '../types';

interface HotspotsViewProps {
  hotspotsData: HotspotsData | null;
  onSelectImpactNode: (filePath: string) => void;
  onExplainNode: (filePath: string) => void;
}

export const HotspotsView: React.FC<HotspotsViewProps> = ({
  hotspotsData,
  onSelectImpactNode,
  onExplainNode,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  if (!hotspotsData) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/50 rounded-2xl border border-slate-800">
        Loading hotspot risk analysis...
      </div>
    );
  }

  const { total_hotspots, hotspots } = hotspotsData;

  const filteredHotspots = hotspots.filter((h) =>
    h.file_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 rounded-2xl border border-orange-500/30 bg-orange-500/10 backdrop-blur-sm flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30 shrink-0">
            <Flame className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">
              Codebase Architectural Hotspots ({total_hotspots})
            </h3>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              Hotspots identify high-risk files combining frequent churn (revision volatility) with high afferent coupling (structural centrality) and cyclomatic complexity. Modifications here carry outsized regression risk.
            </p>
          </div>
        </div>

        <div className="relative shrink-0 hidden sm:block">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search hotspots..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 pr-3 py-1.5 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-orange-500 w-52"
          />
        </div>
      </div>

      {/* Hotspots Table */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-800/40 text-slate-400 uppercase font-semibold text-[11px] tracking-wider">
                <th className="py-3.5 px-4 w-12 text-center">Rank</th>
                <th className="py-3.5 px-4">File Path</th>
                <th className="py-3.5 px-4">Risk Score</th>
                <th className="py-3.5 px-4">Churn</th>
                <th className="py-3.5 px-4">Centrality</th>
                <th className="py-3.5 px-4">Complexity</th>
                <th className="py-3.5 px-4">Diagnostic Rationale</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredHotspots.map((h, idx) => {
                const scoreColor =
                  h.score >= 50
                    ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
                    : h.score >= 20
                    ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
                    : 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30';

                return (
                  <tr
                    key={h.id || idx}
                    className="hover:bg-slate-850/60 transition-colors group"
                  >
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-400">
                      #{idx + 1}
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="font-mono font-medium text-slate-200 break-all">
                        {h.file_path}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex px-2.5 py-1 text-xs font-bold rounded-lg border font-mono ${scoreColor}`}
                      >
                        {h.score.toFixed(1)}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {h.churn_score.toFixed(2)}
                    </td>

                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {h.centrality_score.toFixed(2)}
                    </td>

                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {h.complexity_score.toFixed(1)}
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate" title={h.rationale}>
                      {h.rationale}
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => onSelectImpactNode(h.file_path)}
                          title="Calculate Blast Radius"
                          className="p-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 transition-colors"
                        >
                          <Zap className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => onExplainNode(h.file_path)}
                          title="Explain with AI"
                          className="p-1.5 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 transition-colors"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
