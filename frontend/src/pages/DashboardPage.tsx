import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { workflowAPI, approvalAPI } from '@/services/api';
import type { Workflow, Metrics, Approval } from '@/types';
import { statusBg, formatDate, formatDuration } from '@/lib/utils';
import { usePolling } from '@/hooks/usePolling';
import { PlusCircle, CheckSquare, Clock, TrendingUp, AlertTriangle, Activity } from 'lucide-react';

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
        </div>
        <Icon className={`w-8 h-8 ${color} opacity-50`} />
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([]);

  const fetchData = async () => {
    try {
      const [m, w, a] = await Promise.all([
        workflowAPI.metrics(),
        workflowAPI.list(5),
        approvalAPI.list('pending'),
      ]);
      setMetrics(m.data);
      setWorkflows(w.data);
      setPendingApprovals(a.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchData(); }, []);
  usePolling(fetchData, 3000);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 text-sm">Real-time workflow orchestration overview</p>
        </div>
        <Link
          to="/tasks/new"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <PlusCircle className="w-4 h-4" />
          New Task
        </Link>
      </div>

      {/* Stats Grid */}
      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Workflows" value={metrics.total} icon={Activity} color="text-slate-700" />
          <StatCard label="Completed" value={metrics.completed} icon={TrendingUp} color="text-green-600" />
          <StatCard label="Failed" value={metrics.failed} icon={AlertTriangle} color="text-red-600" />
          <StatCard label="Pending Approvals" value={metrics.pending_approvals} icon={CheckSquare} color="text-orange-600" />
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard label="Running Now" value={metrics.running} icon={Activity} color="text-blue-600" />
          <StatCard label="Success Rate" value={`${metrics.success_rate}%`} icon={TrendingUp} color="text-green-600" />
          <StatCard label="Avg Duration" value={formatDuration(metrics.avg_duration_seconds)} icon={Clock} color="text-slate-600" />
        </div>
      )}

      {/* Pending Approvals */}
      {pendingApprovals.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <CheckSquare className="w-5 h-5 text-orange-600" />
            <h2 className="font-semibold text-orange-800">Pending Approvals ({pendingApprovals.length})</h2>
          </div>
          <div className="space-y-2">
            {pendingApprovals.slice(0, 3).map((a) => (
              <div key={a.id} className="bg-white rounded-lg p-3 border border-orange-100">
                <p className="text-sm font-medium text-slate-800">{a.action_description}</p>
                <p className="text-xs text-slate-500 mt-1">Agent: {a.requesting_agent} · {formatDate(a.created_at)}</p>
                <Link to="/approvals" className="text-xs text-orange-600 hover:underline mt-1 block">
                  Review →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Workflows */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-800">Recent Workflows</h2>
          <Link to="/history" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>
        <div className="space-y-2">
          {workflows.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border border-slate-100">
              <p className="text-slate-400 text-sm">No workflows yet.</p>
              <Link to="/tasks/new" className="text-blue-600 text-sm hover:underline mt-1 block">
                Create your first task →
              </Link>
            </div>
          )}
          {workflows.map((w) => (
            <Link
              key={w.id}
              to={`/workflows/${w.id}`}
              className="flex items-center justify-between bg-white rounded-xl border border-slate-100 p-4 hover:border-blue-200 hover:shadow-sm transition-all"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800 truncate">{w.task}</p>
                <p className="text-xs text-slate-400 mt-1">
                  {formatDate(w.started_at)} · {w.current_agent || 'pending'}
                </p>
              </div>
              <div className="ml-4 flex-shrink-0">
                <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${statusBg(w.status)}`}>
                  {w.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
