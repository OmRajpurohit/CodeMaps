import React, { useState } from 'react';
import { Plus, X, FolderGit2, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import type { Repository } from '../types';

interface AddRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRepoAdded: (newRepo: Repository) => void;
}

export const AddRepoModal: React.FC<AddRepoModalProps> = ({
  isOpen,
  onClose,
  onRepoAdded,
}) => {
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [defaultBranch, setDefaultBranch] = useState('main');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const repo = await api.registerRepository({
        url: url.trim(),
        name: name.trim() || undefined,
        default_branch: defaultBranch.trim() || 'main',
      });
      onRepoAdded(repo);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to register repository.');
    } finally {
      setIsLoading(false);
    }
  };

  const setPreset = (presetUrl: string, presetName: string, presetBranch = 'main') => {
    setUrl(presetUrl);
    setName(presetName);
    setDefaultBranch(presetBranch);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              <FolderGit2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Register Git Repository</h3>
              <p className="text-xs text-slate-400">
                Track a public GitHub repository, private Git repository, or local folder.
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
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Repository URL or Local Path:
            </label>
            <input
              type="text"
              placeholder="https://github.com/owner/repo.git or C:\path\to\folder"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-3.5 py-2 text-xs font-mono rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Display Name (Optional):
              </label>
              <input
                type="text"
                placeholder="e.g. MyService"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Default Branch:
              </label>
              <input
                type="text"
                placeholder="main"
                value={defaultBranch}
                onChange={(e) => setDefaultBranch(e.target.value)}
                className="w-full px-3.5 py-2 text-xs font-mono rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Quick Preset Buttons */}
          <div>
            <span className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Quick Presets:
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() =>
                  setPreset(
                    'https://github.com/OmRajpurohit/movie-recommender',
                    'movie_recommender',
                    'main'
                  )
                }
                className="px-2.5 py-1 text-[11px] rounded-lg bg-slate-800 hover:bg-slate-750 text-indigo-300 border border-slate-700 transition-colors"
              >
                movie-recommender
              </button>
              <button
                type="button"
                onClick={() =>
                  setPreset(
                    'https://github.com/OmRajpurohit/palak_gold',
                    'palak_gold',
                    'main'
                  )
                }
                className="px-2.5 py-1 text-[11px] rounded-lg bg-slate-800 hover:bg-slate-750 text-indigo-300 border border-slate-700 transition-colors"
              >
                palak_gold
              </button>
              <button
                type="button"
                onClick={() =>
                  setPreset(
                    'C:/Users/Mataji Jewellers/OneDrive/Desktop/codeMaps',
                    'CodeAtlas Engine',
                    'main'
                  )
                }
                className="px-2.5 py-1 text-[11px] rounded-lg bg-slate-800 hover:bg-slate-750 text-cyan-300 border border-slate-700 transition-colors"
              >
                CodeAtlas Local Project
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
              {error}
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading || !url.trim()}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors disabled:bg-slate-800 disabled:text-slate-500 shadow-md shadow-indigo-600/20"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Validating & Registering...</span>
                </>
              ) : (
                <>
                  <Plus className="w-3.5 h-3.5" />
                  <span>Register Repository</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
