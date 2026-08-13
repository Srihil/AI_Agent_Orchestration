import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { workflowAPI } from '@/services/api';
import type { Workflow } from '@/types';
import { WorkflowGraph } from '@/components/WorkflowGraph';
import { statusBg, formatDate } from '@/lib/utils';
import { usePolling } from '@/hooks/usePolling';
import { ArrowLeft, Clock, Bot, Wrench } from 'lucide-react';

export function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchWorkflow = async () => {
    if (!id) return;
    try {
      const res = await workflowAPI.get(id);
      setWorkflow(res.data);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchWorkflow(); }, [id]);

  const isActive = workflow?.status === 'running' || workflow?.status === 'pending';
  usePolling(fetchWorkflow, 2000, isActive);

  if (loading) return <div className="p-6 text-slate-500">Loading...</div>;
  if (!workflow) return <div className="p-6 text-slate-500">Workflow not found.</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/" className="text-slate-400 hover:text-slate-600">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-slate-900 truncate">{workflow.task}</h1>
          <p className="text-sm text-slate-400 mt-0.5">Started {formatDate(workflow.started_at)}</p>
        </div>
        <span className={`text-sm px-3 py-1 rounded-full border font-medium flex-shrink-0 ${statusBg(workflow.status)}`}>
          {workflow.status}
        </span>
      </div>

      {/* Status Banner */}
      {workflow.status === 'running' && workflow.current_agent && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
          <span className="text-sm text-blue-800 font-medium capitalize">
            {workflow.current_agent} is working...
          </span>
          <span className="text-xs text-blue-500 ml-auto">
            Step {workflow.step_count} / {workflow.max_steps}
          </span>
        </div>
      )}

      {workflow.status === 'paused' && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-orange-800">Waiting for Human Approval</p>
            <p className="text-xs text-orange-600 mt-1">The workflow is paused until you review and approve the action.</p>
          </div>
          <Link
            to="/approvals"
            className="bg-orange-600 hover:bg-orange-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            Review
          </Link>
        </div>
      )}

      {workflow.status === 'failed' && workflow.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm font-semibold text-red-800">Workflow Failed</p>
          <p className="text-xs text-red-600 mt-1">{workflow.error_message}</p>
        </div>
      )}

      {/* Workflow Graph */}
      <div>
        <h2 className="font-semibold text-slate-800 mb-3">Execution Graph</h2>
        <WorkflowGraph workflow={workflow} />
      </div>

      {/* Final Response */}
      {workflow.final_response && (
        <div>
          <h2 className="font-semibold text-slate-800 mb-3">Final Response</h2>
          <div className="bg-white rounded-xl border border-slate-100 p-5 shadow-sm">
            <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
              {workflow.final_response}
            </pre>
          </div>
        </div>
      )}

      {/* Execution Trace */}
      {workflow.events && workflow.events.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-800 mb-3">Execution Trace</h2>
          <div className="space-y-2">
            {workflow.events.map((event) => (
              <div
                key={event.id}
                className="bg-white rounded-lg border border-slate-100 p-3 flex items-start gap-3"
              >
                <div className="flex-shrink-0 mt-0.5">
                  {event.tool_name ? (
                    <Wrench className="w-4 h-4 text-purple-400" />
                  ) : (
                    <Bot className="w-4 h-4 text-blue-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-slate-600 capitalize">
                      {event.agent_name || 'system'}
                    </span>
                    {event.tool_name && (
                      <span className="text-xs bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">
                        {event.tool_name}
                      </span>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded border ${statusBg(event.status)}`}>
                      {event.status}
                    </span>
                    {event.duration_ms && (
                      <span className="text-xs text-slate-400 flex items-center gap-1 ml-auto">
                        <Clock className="w-3 h-3" />
                        {event.duration_ms}ms
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{event.action}</p>
                  {event.result_summary && (
                    <p className="text-xs text-slate-600 mt-1 truncate">{event.result_summary}</p>
                  )}
                  {event.error && (
                    <p className="text-xs text-red-500 mt-1">{event.error}</p>
                  )}
                </div>
                <div className="text-xs text-slate-300 flex-shrink-0">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
