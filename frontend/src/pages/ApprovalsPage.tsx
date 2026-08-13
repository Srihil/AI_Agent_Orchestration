import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { approvalAPI } from '@/services/api';
import type { Approval } from '@/types';
import { statusBg, formatDate } from '@/lib/utils';
import { usePolling } from '@/hooks/usePolling';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

function RiskBadge({ risk }: { risk: string }) {
  const colors: Record<string, string> = {
    low: 'text-green-600 bg-green-50 border-green-200',
    medium: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    high: 'text-red-600 bg-red-50 border-red-200',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${colors[risk] || colors.medium}`}>
      {risk} risk
    </span>
  );
}

export function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [filter, setFilter] = useState<'pending' | 'all'>('pending');
  const [deciding, setDeciding] = useState<string | null>(null);
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});

  const fetchApprovals = async () => {
    try {
      const res = await approvalAPI.list(filter);
      setApprovals(res.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchApprovals(); }, [filter]);
  usePolling(fetchApprovals, 3000, filter === 'pending');

  const handleDecision = async (approval: Approval, decision: 'approve' | 'reject') => {
    setDeciding(approval.id);
    try {
      const note = decisionNotes[approval.id];
      if (decision === 'approve') {
        await approvalAPI.approve(approval.id, note);
      } else {
        await approvalAPI.reject(approval.id, note);
      }
      await fetchApprovals();
    } catch (e) {
      console.error(e);
    } finally {
      setDeciding(null);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Human Approvals</h1>
          <p className="text-slate-500 text-sm mt-1">Review and approve or reject pending workflow actions</p>
        </div>
        <div className="flex gap-2">
          {(['pending', 'all'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-sm px-3 py-1.5 rounded-lg transition-colors ${
                filter === f ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:border-blue-300'
              }`}
            >
              {f === 'pending' ? 'Pending' : 'All'}
            </button>
          ))}
        </div>
      </div>

      {approvals.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-100">
          <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-3" />
          <p className="text-slate-500">No {filter === 'pending' ? 'pending' : ''} approvals</p>
        </div>
      )}

      <div className="space-y-4">
        {approvals.map((approval) => (
          <div key={approval.id} className="bg-white rounded-xl border border-slate-100 shadow-sm overflow-hidden">
            {approval.status === 'pending' && (
              <div className="bg-orange-50 border-b border-orange-100 px-5 py-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-500" />
                <span className="text-xs font-medium text-orange-700">Action Required</span>
              </div>
            )}

            <div className="p-5 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-semibold text-slate-800">{approval.action_description}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">Agent: {approval.requesting_agent}</span>
                    <span className="text-xs text-slate-300">·</span>
                    <RiskBadge risk={approval.risk_level} />
                    <span className="text-xs text-slate-300">·</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${statusBg(approval.status)}`}>
                      {approval.status}
                    </span>
                  </div>
                </div>
                <Link
                  to={`/workflows/${approval.workflow_run_id}`}
                  className="text-xs text-blue-600 hover:underline flex-shrink-0"
                >
                  View workflow →
                </Link>
              </div>

              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-xs font-medium text-slate-500 mb-1">Reason</p>
                <p className="text-sm text-slate-700">{approval.reason}</p>
              </div>

              <p className="text-xs text-slate-400">Requested {formatDate(approval.created_at)}</p>

              {approval.decided_at && (
                <p className="text-xs text-slate-400">
                  Decided {formatDate(approval.decided_at)}
                  {approval.decision_note && ` · "${approval.decision_note}"`}
                </p>
              )}

              {approval.status === 'pending' && (
                <div className="space-y-3">
                  <input
                    type="text"
                    placeholder="Optional note..."
                    value={decisionNotes[approval.id] || ''}
                    onChange={(e) => setDecisionNotes(prev => ({ ...prev, [approval.id]: e.target.value }))}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleDecision(approval, 'approve')}
                      disabled={deciding === approval.id}
                      className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleDecision(approval, 'reject')}
                      disabled={deciding === approval.id}
                      className="flex-1 flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      <XCircle className="w-4 h-4" />
                      Reject
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
