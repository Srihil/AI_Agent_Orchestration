import ReactFlow, { Node, Edge, Background, Controls, NodeProps } from 'reactflow';
import 'reactflow/dist/style.css';
import type { Workflow } from '@/types';

const AGENT_ORDER = ['user', 'supervisor', 'researcher', 'analyst', 'writer', 'reviewer', 'finalize'];

function getNodeStatus(agentName: string, workflow: Workflow): string {
  if (!workflow.events || workflow.events.length === 0) {
    return agentName === 'user' ? 'completed' : 'pending';
  }

  const events = workflow.events.filter(
    (e) => e.agent_name === agentName || (agentName === 'user' && e.action.includes('start'))
  );

  if (agentName === 'user') return 'completed';

  if (workflow.status === 'completed' && agentName === 'finalize') return 'completed';
  if (workflow.current_agent === agentName && workflow.status === 'running') return 'running';
  if (workflow.current_agent === agentName && workflow.status === 'paused') return 'paused';

  const hasSuccess = events.some((e) => e.status === 'success');
  const hasFailed = events.some((e) => e.status === 'failed');

  if (hasSuccess) return 'completed';
  if (hasFailed) return 'failed';
  if (events.length > 0) return 'running';

  return 'pending';
}

const statusConfig: Record<string, { bg: string; border: string; dot: string; label: string }> = {
  pending: { bg: 'bg-slate-100', border: 'border-slate-200', dot: 'bg-slate-300', label: 'Pending' },
  running: { bg: 'bg-blue-50', border: 'border-blue-300', dot: 'bg-blue-500 animate-pulse', label: 'Running' },
  paused: { bg: 'bg-orange-50', border: 'border-orange-300', dot: 'bg-orange-500', label: 'Awaiting Approval' },
  completed: { bg: 'bg-green-50', border: 'border-green-300', dot: 'bg-green-500', label: 'Done' },
  failed: { bg: 'bg-red-50', border: 'border-red-300', dot: 'bg-red-500', label: 'Failed' },
  waiting: { bg: 'bg-yellow-50', border: 'border-yellow-300', dot: 'bg-yellow-500', label: 'Waiting' },
};

function AgentNode({ data }: NodeProps) {
  const config = statusConfig[data.status] || statusConfig.pending;
  return (
    <div className={`px-4 py-3 rounded-xl border-2 ${config.bg} ${config.border} min-w-[140px] shadow-sm`}>
      <div className="flex items-center gap-2">
        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${config.dot}`} />
        <span className="text-sm font-semibold text-slate-700 capitalize">{data.label}</span>
      </div>
      <div className="text-xs text-slate-400 mt-1 pl-4">{config.label}</div>
    </div>
  );
}

const nodeTypes = { agentNode: AgentNode };

interface Props { workflow: Workflow }

export function WorkflowGraph({ workflow }: Props) {
  const visibleAgents = AGENT_ORDER.filter((a) => {
    if (a === 'finalize') return workflow.status === 'completed';
    return true;
  });

  const nodes: Node[] = visibleAgents.map((agent, i) => ({
    id: agent,
    type: 'agentNode',
    position: { x: 250, y: i * 110 },
    data: {
      label: agent === 'finalize' ? 'Final Response' : agent,
      status: getNodeStatus(agent, workflow),
    },
  }));

  // Add tools node branching from researcher
  if (workflow.events?.some((e) => e.tool_name)) {
    nodes.push({
      id: 'tools',
      type: 'agentNode',
      position: { x: 450, y: 2 * 110 },
      data: { label: 'Tools', status: workflow.events.some(e => e.tool_name && e.status === 'success') ? 'completed' : 'pending' },
    });
  }

  const edges: Edge[] = [];
  for (let i = 0; i < visibleAgents.length - 1; i++) {
    edges.push({
      id: `${visibleAgents[i]}-${visibleAgents[i + 1]}`,
      source: visibleAgents[i],
      target: visibleAgents[i + 1],
      animated: workflow.status === 'running',
      style: { stroke: '#94a3b8' },
    });
  }

  if (workflow.events?.some((e) => e.tool_name)) {
    edges.push({ id: 'researcher-tools', source: 'researcher', target: 'tools', style: { stroke: '#94a3b8', strokeDasharray: '4' } });
    edges.push({ id: 'tools-researcher', source: 'tools', target: 'analyst', style: { stroke: '#94a3b8', strokeDasharray: '4' } });
  }

  return (
    <div className="h-[500px] w-full bg-slate-50 rounded-xl border border-slate-200">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesConnectable={false}
        nodesDraggable={false}
        elementsSelectable={false}
      >
        <Background color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
