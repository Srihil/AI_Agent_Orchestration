import { useState, useEffect } from 'react';
import { agentAPI } from '@/services/api';
import type { AgentStats } from '@/types';
import { Bot, Wrench, TrendingUp } from 'lucide-react';

const AGENT_ICONS: Record<string, string> = {
  supervisor: '🎯',
  researcher: '🔍',
  analyst: '📊',
  writer: '✍️',
  reviewer: '✅',
};

export function AgentsPage() {
  const [agents, setAgents] = useState<AgentStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    agentAPI.list()
      .then((res) => setAgents(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-slate-500">Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Agents</h1>
        <p className="text-slate-500 text-sm mt-1">
          Specialized agents with real execution statistics from your workflow history
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {agents.map((agent) => (
          <div key={agent.agent_name} className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="text-2xl">{AGENT_ICONS[agent.agent_name] || '🤖'}</div>
              <div>
                <h2 className="font-bold text-slate-800 capitalize">{agent.agent_name} Agent</h2>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{agent.description}</p>
              </div>
            </div>

            {agent.tools.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Wrench className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Available Tools</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {agent.tools.map((tool) => (
                    <span key={tool} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-3 pt-3 border-t border-slate-50">
              <div className="text-center">
                <div className="flex items-center justify-center gap-1">
                  <Bot className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-lg font-bold text-slate-700">{agent.total_executions}</span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">Total Runs</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-lg font-bold text-green-600">{agent.success_rate}%</span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">Success Rate</p>
              </div>
              <div className="text-center">
                <span className="text-lg font-bold text-slate-700">
                  {agent.avg_duration_ms ? `${Math.round(agent.avg_duration_ms / 1000)}s` : '—'}
                </span>
                <p className="text-xs text-slate-400 mt-0.5">Avg Duration</p>
              </div>
            </div>

            {agent.total_executions > 0 && (
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Success</span>
                  <span>{agent.successful_executions} / {agent.total_executions}</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 rounded-full"
                    style={{ width: `${agent.success_rate}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
