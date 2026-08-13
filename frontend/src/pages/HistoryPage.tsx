import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { workflowAPI } from '@/services/api';
import type { Workflow } from '@/types';
import { statusBg, formatDate } from '@/lib/utils';

export function HistoryPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    workflowAPI.list(20, page * 20)
      .then((res) => setWorkflows(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  async function handleDelete(id: string) {
    if (!window.confirm('Delete this workflow run? This cannot be undone.')) return;
    setDeleting(id);
    try {
      await workflowAPI.cancel(id);
      setWorkflows(prev => prev.filter(w => w.id !== id));
    } catch {
      // silently fail — item stays in the list
    } finally {
      setDeleting(null);
    }
  }

  if (loading) return <div className="p-6 text-slate-500">Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Execution History</h1>
        <p className="text-slate-500 text-sm mt-1">All workflow runs, newest first</p>
      </div>

      {workflows.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-100">
          <p className="text-slate-400">No workflow history yet.</p>
          <Link to="/tasks/new" className="text-blue-600 text-sm hover:underline mt-1 block">
            Start your first task →
          </Link>
        </div>
      )}

      <div className="space-y-2">
        {workflows.map((w) => (
          <div
            key={w.id}
            className="group flex items-center bg-white rounded-xl border border-slate-100 hover:border-blue-200 hover:shadow-sm transition-all"
          >
            <Link
              to={`/workflows/${w.id}`}
              className="flex items-center justify-between flex-1 min-w-0 p-4"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800 truncate group-hover:text-blue-600 transition-colors">
                  {w.task}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-xs text-slate-400">{formatDate(w.started_at)}</span>
                  {w.completed_at && (
                    <>
                      <span className="text-xs text-slate-300">·</span>
                      <span className="text-xs text-slate-400">
                        {Math.round((new Date(w.completed_at).getTime() - new Date(w.started_at).getTime()) / 1000)}s
                      </span>
                    </>
                  )}
                  <span className="text-xs text-slate-300">·</span>
                  <span className="text-xs text-slate-400">{w.step_count} steps</span>
                </div>
              </div>
              <div className="ml-4 flex-shrink-0">
                <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${statusBg(w.status)}`}>
                  {w.status}
                </span>
              </div>
            </Link>

            <button
              onClick={() => handleDelete(w.id)}
              disabled={deleting === w.id}
              title="Delete"
              className="mr-3 p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-30 flex-shrink-0"
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>

      {workflows.length === 20 && (
        <div className="flex justify-center">
          <button
            onClick={() => setPage(p => p + 1)}
            className="text-sm text-blue-600 hover:underline"
          >
            Load more
          </button>
        </div>
      )}
    </div>
  );
}
