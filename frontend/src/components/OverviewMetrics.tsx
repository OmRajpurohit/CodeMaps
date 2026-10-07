import React from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Flame,
  Network,
  RotateCcw,
  GitBranch,
  Terminal,
} from 'lucide-react';
import type { RepositoryOverview } from '../types';

interface OverviewMetricsProps {
  overview: RepositoryOverview;
  onNavigateTab: (tab: string) => void;
}

export const OverviewMetrics: React.FC<OverviewMetricsProps> = ({ overview, onNavigateTab }) => {
  const health = overview.health_score;

  const getHealthMeta = (score: number) => {
    if (score >= 90) {
      return {
        label: 'Optimal Architecture',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500/10',
        borderColor: 'border-emerald-500/30',
        barColor: 'bg-emerald-500',
        desc: 'Clean layer boundaries, zero critical cycles, low structural coupling.',
      };
    }
    if (score >= 70) {
      return {
        label: 'Moderate Debt',
        color: 'text-amber-400',
        bgColor: 'bg-amber-500/10',
        borderColor: 'border-amber-500/30',
        barColor: 'bg-amber-500',
        desc: 'Some cyclic dependencies or layer constraint warnings present.',
      };
    }
    return {
      label: 'High Architectural Risk',
      color: 'text-rose-400',
      bgColor: 'bg-rose-500/10',
      borderColor: 'border-rose-500/30',
      barColor: 'bg-rose-500',
      desc: 'Critical circular dependency clusters or extensive layer violations detected.',
    };
  };

  const healthMeta = getHealthMeta(health);

  // Language bar percentages
  const languages = overview.languages_breakdown || {};
  const totalLangLoc = Object.values(languages).reduce((acc, val) => acc + val, 0) || 1;

  const langColorMap: Record<string, string> = {
    Python: 'bg-blue-500',
    TypeScript: 'bg-cyan-500',
    JavaScript: 'bg-amber-400',
    HTML: 'bg-orange-500',
    CSS: 'bg-purple-500',
    JSON: 'bg-emerald-500',
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Health Score & Repo Identity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Health Score Gauge Card */}
        <div className={`p-6 rounded-2xl border ${healthMeta.borderColor} ${healthMeta.bgColor} relative overflow-hidden backdrop-blur-sm`}>
          <div className="flex items-start justify-between">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Architecture Health Score
              </span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className={`text-5xl font-black tracking-tight ${healthMeta.color}`}>
                  {health.toFixed(0)}
                </span>
                <span className="text-xl font-medium text-slate-400">/ 100</span>
              </div>
              <p className={`text-sm font-semibold mt-1 ${healthMeta.color}`}>
                {healthMeta.label}
              </p>
            </div>
            <div className={`p-3 rounded-xl border ${healthMeta.borderColor} ${healthMeta.bgColor}`}>
              {health >= 70 ? (
                <ShieldCheck className={`w-8 h-8 ${healthMeta.color}`} />
              ) : (
                <ShieldAlert className={`w-8 h-8 ${healthMeta.color}`} />
              )}
            </div>
          </div>

          <div className="w-full bg-slate-800/80 rounded-full h-2 mt-5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${healthMeta.barColor}`}
              style={{ width: `${Math.min(100, Math.max(5, health))}%` }}
            />
          </div>

          <p className="text-xs text-slate-400 mt-3 leading-relaxed">
            {healthMeta.desc}
          </p>
        </div>

        {/* Repository Overview Summary */}
        <div className="lg:col-span-2 p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <Terminal className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight">{overview.name}</h3>
                  <a
                    href={overview.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-indigo-400 hover:underline break-all"
                  >
                    {overview.url}
                  </a>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
                  <GitBranch className="w-3 h-3 text-slate-400" />
                  {overview.commit_sha ? overview.commit_sha.substring(0, 7) : 'HEAD'}
                </span>
                {overview.primary_language && (
                  <span className="px-2.5 py-1 text-xs font-semibold rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                    {overview.primary_language}
                  </span>
                )}
              </div>
            </div>

            {/* Languages Bar */}
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span className="font-medium">Language Distribution</span>
                <span>{overview.total_loc.toLocaleString()} Total LOC</span>
              </div>
              <div className="w-full h-3 rounded-full overflow-hidden flex bg-slate-800">
                {Object.entries(languages).map(([lang, loc]) => {
                  const pct = (loc / totalLangLoc) * 100;
                  const color = langColorMap[lang] || 'bg-slate-500';
                  return (
                    <div
                      key={lang}
                      style={{ width: `${pct}%` }}
                      title={`${lang}: ${loc.toLocaleString()} lines (${pct.toFixed(1)}%)`}
                      className={`h-full ${color} transition-all duration-500 first:rounded-l-full last:rounded-r-full`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-4 mt-3">
                {Object.entries(languages).map(([lang, loc]) => {
                  const pct = (loc / totalLangLoc) * 100;
                  const color = langColorMap[lang] || 'bg-slate-500';
                  return (
                    <div key={lang} className="flex items-center gap-1.5 text-xs">
                      <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                      <span className="font-medium text-slate-200">{lang}</span>
                      <span className="text-slate-500 font-mono">({pct.toFixed(0)}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 pt-4 mt-4 border-t border-slate-800/80">
            <div>
              <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Files</span>
              <p className="text-xl font-bold text-white mt-0.5">{overview.total_files}</p>
            </div>
            <div>
              <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">Symbols</span>
              <p className="text-xl font-bold text-white mt-0.5">{overview.total_symbols}</p>
            </div>
            <div>
              <span className="text-[11px] uppercase tracking-wider text-slate-400 font-medium">LOC / File</span>
              <p className="text-xl font-bold text-white mt-0.5">
                {overview.total_files > 0 ? Math.round(overview.total_loc / overview.total_files) : 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Diagnostic Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Cycles Card */}
        <div
          onClick={() => onNavigateTab('cycles')}
          className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
              Circular Cycles
            </span>
            <div className={`p-2 rounded-lg ${overview.total_cycles > 0 ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
              <RotateCcw className="w-4 h-4 group-hover:rotate-45 transition-transform" />
            </div>
          </div>
          <div className="mt-3">
            <span className={`text-3xl font-extrabold ${overview.total_cycles > 0 ? 'text-rose-400' : 'text-slate-100'}`}>
              {overview.total_cycles}
            </span>
            <p className="text-xs text-slate-400 mt-1">
              {overview.total_cycles === 0 ? 'Zero cyclic loops detected' : 'Strongly connected clusters'}
            </p>
          </div>
        </div>

        {/* Layer Violations Card */}
        <div
          onClick={() => onNavigateTab('violations')}
          className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
              Layer Violations
            </span>
            <div className={`p-2 rounded-lg ${overview.total_violations > 0 ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
              <ShieldAlert className="w-4 h-4 group-hover:scale-110 transition-transform" />
            </div>
          </div>
          <div className="mt-3">
            <span className={`text-3xl font-extrabold ${overview.total_violations > 0 ? 'text-amber-400' : 'text-slate-100'}`}>
              {overview.total_violations}
            </span>
            <p className="text-xs text-slate-400 mt-1">
              {overview.total_violations === 0 ? 'Boundary rules respected' : 'Architecture rule deviations'}
            </p>
          </div>
        </div>

        {/* Hotspots Card */}
        <div
          onClick={() => onNavigateTab('hotspots')}
          className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
              High-Debt Hotspots
            </span>
            <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400 border border-orange-500/20">
              <Flame className="w-4 h-4 group-hover:scale-110 transition-transform" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-slate-100">
              {overview.total_hotspots}
            </span>
            <p className="text-xs text-slate-400 mt-1">
              High churn & high coupling files
            </p>
          </div>
        </div>

        {/* Knowledge Graph Card */}
        <div
          onClick={() => onNavigateTab('graph')}
          className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-indigo-500/50 hover:bg-slate-900 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
              Knowledge Graph
            </span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Network className="w-4 h-4 group-hover:scale-110 transition-transform" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-indigo-400">
              {overview.total_symbols}
            </span>
            <p className="text-xs text-slate-400 mt-1">
              Explore interactive dependency graph →
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
