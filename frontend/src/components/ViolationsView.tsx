import React, { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Filter,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import type { ViolationsData } from '../types';

interface ViolationsViewProps {
  violationsData: ViolationsData | null;
  onExplainViolation: (filePath: string, message: string) => void;
}

export const ViolationsView: React.FC<ViolationsViewProps> = ({
  violationsData,
  onExplainViolation,
}) => {
  const [severityFilter, setSeverityFilter] = useState<'all' | 'error' | 'warning'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  if (!violationsData) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/50 rounded-2xl border border-slate-800">
        Loading architecture violations...
      </div>
    );
  }

  const { total_violations, violations } = violationsData;

  const errorCount = violations.filter((v) => v.severity === 'error').length;
  const warningCount = violations.filter((v) => v.severity === 'warning').length;

  const filteredViolations = violations.filter((v) => {
    if (severityFilter !== 'all' && v.severity !== severityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        v.rule_name.toLowerCase().includes(q) ||
        v.source_file_path.toLowerCase().includes(q) ||
        v.target_file_path.toLowerCase().includes(q) ||
        v.message.toLowerCase().includes(q)
      );
    }
    return true;
  });

  if (total_violations === 0) {
    return (
      <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 backdrop-blur-sm max-w-2xl mx-auto my-8">
        <div className="inline-flex p-4 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-4">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <h3 className="text-xl font-bold text-white">Zero Architecture Violations</h3>
        <p className="text-sm text-slate-400 mt-2 leading-relaxed">
          All dependency edges comply strictly with defined architectural layers and encapsulation boundaries. No backwards or forbidden imports detected.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <span className="text-xs uppercase font-medium text-slate-400 tracking-wider">
            Total Violations
          </span>
          <p className="text-3xl font-extrabold text-white mt-1">{total_violations}</p>
        </div>
        <div className="p-5 rounded-xl border border-rose-500/30 bg-rose-500/10 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-medium text-rose-300 tracking-wider">
              Critical Errors
            </span>
            <AlertCircle className="w-4 h-4 text-rose-400" />
          </div>
          <p className="text-3xl font-extrabold text-rose-400 mt-1">{errorCount}</p>
        </div>
        <div className="p-5 rounded-xl border border-amber-500/30 bg-amber-500/10 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-medium text-amber-300 tracking-wider">
              Warnings
            </span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-3xl font-extrabold text-amber-400 mt-1">{warningCount}</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filter by Severity:</span>
          <div className="flex items-center gap-1 bg-slate-800 p-0.5 rounded-lg border border-slate-700 text-xs">
            {(['all', 'error', 'warning'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-3 py-1 rounded font-medium capitalize transition-colors ${
                  severityFilter === sev
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <input
          type="text"
          placeholder="Filter by rule or file path..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-64"
        />
      </div>

      {/* Violations List */}
      <div className="space-y-3">
        {filteredViolations.map((v) => (
          <div
            key={v.id}
            className={`p-5 rounded-xl border transition-colors backdrop-blur-sm ${
              v.severity === 'error'
                ? 'border-rose-500/30 bg-slate-900/80 hover:border-rose-500/60'
                : 'border-amber-500/30 bg-slate-900/80 hover:border-amber-500/60'
            }`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`flex items-center gap-1 px-2 py-0.5 text-[11px] font-bold uppercase rounded ${
                      v.severity === 'error'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {v.severity === 'error' ? (
                      <AlertCircle className="w-3 h-3" />
                    ) : (
                      <AlertTriangle className="w-3 h-3" />
                    )}
                    {v.severity}
                  </span>
                  <span className="text-xs font-semibold text-slate-200">{v.rule_name}</span>
                </div>
                <p className="text-sm text-slate-300 font-medium mt-1">{v.message}</p>
              </div>

              <button
                onClick={() => onExplainViolation(v.source_file_path, v.message)}
                className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>Explain Violation</span>
              </button>
            </div>

            {/* Boundary Traversal Link */}
            <div className="flex flex-wrap items-center gap-2.5 mt-4 pt-3 border-t border-slate-800 text-xs font-mono">
              <div className="flex items-center gap-1.5 bg-slate-800/80 px-2.5 py-1 rounded border border-slate-700 text-slate-300">
                <span className="text-[10px] text-slate-400 font-sans uppercase">Source:</span>
                <span>{v.source_file_path}</span>
                {v.layer_from && (
                  <span className="text-[10px] font-sans px-1 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                    [{v.layer_from}]
                  </span>
                )}
              </div>

              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />

              <div className="flex items-center gap-1.5 bg-slate-800/80 px-2.5 py-1 rounded border border-slate-700 text-slate-300">
                <span className="text-[10px] text-slate-400 font-sans uppercase">Target:</span>
                <span>{v.target_file_path}</span>
                {v.layer_to && (
                  <span className="text-[10px] font-sans px-1 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                    [{v.layer_to}]
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
