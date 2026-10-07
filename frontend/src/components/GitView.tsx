import React, { useState } from 'react';
import {
  GitCommit as GitCommitIcon,
  User,
  Activity,
} from 'lucide-react';
import type { GitHistoryData } from '../types';

interface GitViewProps {
  gitData: GitHistoryData | null;
}

export const GitView: React.FC<GitViewProps> = ({ gitData }) => {
  const [activeTab, setActiveTab] = useState<'commits' | 'churn'>('commits');

  if (!gitData) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/50 rounded-2xl border border-slate-800">
        Loading Git commit history and churn analytics...
      </div>
    );
  }

  const { commits, file_churns } = gitData;

  return (
    <div className="space-y-6">
      {/* Tab toggle */}
      <div className="flex items-center gap-2 p-1 bg-slate-900 border border-slate-800 rounded-xl w-fit">
        <button
          onClick={() => setActiveTab('commits')}
          className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === 'commits'
              ? 'bg-indigo-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <GitCommitIcon className="w-3.5 h-3.5" />
          <span>Commit Log ({commits.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('churn')}
          className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === 'churn'
              ? 'bg-indigo-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>File Churn & Ownership ({file_churns.length})</span>
        </button>
      </div>

      {activeTab === 'commits' ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-800/40 text-slate-400 uppercase text-[11px] font-semibold">
                  <th className="py-3 px-4">SHA</th>
                  <th className="py-3 px-4">Author</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Commit Message</th>
                  <th className="py-3 px-4 text-right">Changes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {commits.map((c) => (
                  <tr key={c.id || c.commit_sha} className="hover:bg-slate-850/60 transition-colors">
                    <td className="py-3 px-4 font-mono text-indigo-400 font-semibold">
                      {c.commit_sha.substring(0, 7)}
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                        <User className="w-3 h-3 text-slate-400" />
                        {c.author_alias}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(c.authored_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-slate-200 max-w-md truncate" title={c.message}>
                      {c.message}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap font-mono">
                      <span className="text-emerald-400 font-medium">+{c.insertions}</span>
                      <span className="text-slate-600 mx-1">/</span>
                      <span className="text-rose-400 font-medium">-{c.deletions}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-800/40 text-slate-400 uppercase text-[11px] font-semibold">
                  <th className="py-3 px-4">File Path</th>
                  <th className="py-3 px-4">Commits</th>
                  <th className="py-3 px-4">Lines Added</th>
                  <th className="py-3 px-4">Lines Deleted</th>
                  <th className="py-3 px-4">Authors</th>
                  <th className="py-3 px-4">Ownership HHI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {file_churns.map((fc) => (
                  <tr key={fc.id || fc.file_path} className="hover:bg-slate-850/60 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-slate-200 break-all">
                      {fc.file_path}
                    </td>
                    <td className="py-3 px-4 font-mono text-indigo-400 font-bold">
                      {fc.commit_count}
                    </td>
                    <td className="py-3 px-4 font-mono text-emerald-400">
                      +{fc.lines_added.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-rose-400">
                      -{fc.lines_deleted.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {fc.author_count}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {fc.ownership_entropy ? fc.ownership_entropy.toFixed(2) : '1.00'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
