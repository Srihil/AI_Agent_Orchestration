import ReactFlow, {
  Node, Edge, Background, Controls, NodeProps,
  MarkerType, Handle, Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { Workflow } from '@/types';

// ─── status helpers ──────────────────────────────────────────────────────────

function agentStatus(name: string, workflow: Workflow): string {
  if (workflow.status === 'completed' && name === 'finalize') return 'completed';
  if (workflow.current_agent === name)
    return workflow.status === 'paused' ? 'paused' : 'running';
  const evts = workflow.events?.filter(e => e.agent_name === name) ?? [];
  if (evts.some(e => e.status === 'failed'))  return 'failed';
  if (evts.some(e => e.status === 'success')) return 'completed';
  if (evts.length > 0)                        return 'running';
  return 'pending';
}

function toolStatus(workflow: Workflow): string {
  const evts = workflow.events?.filter(e => e.tool_name) ?? [];
  if (evts.some(e => e.status === 'failed'))  return 'failed';
  if (evts.some(e => e.status === 'success')) return 'completed';
  return 'running';
}

function approvalStatus(workflow: Workflow): string {
  if (workflow.status === 'paused')     return 'paused';
  if (workflow.status === 'completed')  return 'completed';
  return 'pending';
}

// ─── node styles ─────────────────────────────────────────────────────────────

const S: Record<string, { bg: string; ring: string; dot: string; text: string; label: string }> = {
  pending:   { bg: 'bg-slate-50',   ring: 'border-slate-200',   dot: 'bg-slate-300',   text: 'text-slate-400',   label: 'Pending' },
  running:   { bg: 'bg-blue-50',    ring: 'border-blue-400',    dot: 'bg-blue-500',    text: 'text-blue-600',    label: 'Running' },
  paused:    { bg: 'bg-amber-50',   ring: 'border-amber-400',   dot: 'bg-amber-500',   text: 'text-amber-600',   label: 'Awaiting Approval' },
  completed: { bg: 'bg-emerald-50', ring: 'border-emerald-400', dot: 'bg-emerald-500', text: 'text-emerald-600', label: 'Done' },
  failed:    { bg: 'bg-red-50',     ring: 'border-red-400',     dot: 'bg-red-500',     text: 'text-red-600',     label: 'Failed' },
};

function AgentNode({ data }: NodeProps) {
  const s = S[data.status as string] ?? S.pending;
  return (
    <>
      <Handle type="target" position={Position.Top}
        style={{ background: '#cbd5e1', width: 8, height: 8, border: 'none' }} />
      <div className={`px-4 py-3 rounded-xl border-2 shadow-sm select-none ${s.bg} ${s.ring}`}
           style={{ minWidth: 148 }}>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${s.dot}${data.status === 'running' ? ' animate-pulse' : ''}`} />
          <span className="text-[13px] font-semibold text-slate-700">{data.label}</span>
        </div>
        <p className={`text-[11px] mt-1 pl-[18px] ${s.text}`}>{s.label}</p>
      </div>
      <Handle type="source" position={Position.Bottom}
        style={{ background: '#cbd5e1', width: 8, height: 8, border: 'none' }} />
    </>
  );
}

const nodeTypes = { agent: AgentNode };

// ─── shared edge presets ─────────────────────────────────────────────────────

const ARROW = { type: MarkerType.ArrowClosed, color: '#94a3b8', width: 18, height: 18 } as const;
const LINE  = { type: 'smoothstep' as const, style: { stroke: '#94a3b8', strokeWidth: 1.8 }, markerEnd: ARROW };
const DASH  = { ...LINE, style: { ...LINE.style, strokeDasharray: '5 4' } };

// ─── layout constants ────────────────────────────────────────────────────────

const CX   = 185;   // x for center-column nodes (Supervisor / Tools / Reviewer / Finalize)
const GAP  = 130;   // vertical gap between rows
const L    = 0;     // Researcher x
const M    = CX;    // Analyst x  (same as CX so supervisor is visually centred over the 3)
const R    = CX * 2; // Writer x

// ─── component ───────────────────────────────────────────────────────────────

interface Props { workflow: Workflow }

export function WorkflowGraph({ workflow }: Props) {
  const hasTools    = !!workflow.events?.some(e => e.tool_name);
  const withApprove = !!workflow.require_approval;

  const nodes: Node[] = [];
  const edges: Edge[]  = [];
  let y = 0;

  function push(id: string, label: string, x: number, status: string) {
    nodes.push({ id, type: 'agent', position: { x, y }, data: { label, status } });
  }

  function link(id: string, src: string, tgt: string, dashed = false) {
    edges.push({ id, source: src, target: tgt, ...(dashed ? DASH : LINE) });
  }

  // Row 1 – Supervisor
  push('supervisor', 'Supervisor', CX, y);
  y += GAP;

  // Row 2 – Branch agents
  push('researcher', 'Researcher', L, y);
  push('analyst',    'Analyst',    M, y);
  push('writer',     'Writer',     R, y);
  link('sv-rs', 'supervisor', 'researcher');
  link('sv-an', 'supervisor', 'analyst');
  link('sv-wr', 'supervisor', 'writer');
  y += GAP;

  // Row 3 – Tools (only when tool calls exist)
  if (hasTools) {
    push('tools', 'Tools', CX, y);
    nodes[nodes.length - 1].data.status = toolStatus(workflow);
    link('rs-tl', 'researcher', 'tools', true);
    link('an-tl', 'analyst',    'tools', true);
    link('wr-tl', 'writer',     'tools', true);
    y += GAP;
  }

  // Row – Reviewer
  push('reviewer', 'Reviewer', CX, y);
  nodes[nodes.length - 1].data.status = agentStatus('reviewer', workflow);
  if (hasTools) {
    link('tl-rv', 'tools', 'reviewer');
  } else {
    link('rs-rv', 'researcher', 'reviewer');
    link('an-rv', 'analyst',    'reviewer');
    link('wr-rv', 'writer',     'reviewer');
  }
  y += GAP;

  // Row – Approval gate (conditional)
  if (withApprove) {
    push('approval', 'Approval Gate', CX, y);
    nodes[nodes.length - 1].data.status = approvalStatus(workflow);
    link('rv-ap', 'reviewer', 'approval');
    y += GAP;
  }

  // Row – Final Response (only when completed)
  if (workflow.status === 'completed') {
    push('finalize', 'Final Response', CX, y);
    nodes[nodes.length - 1].data.status = 'completed';
    link('ap-fn', withApprove ? 'approval' : 'reviewer', 'finalize');
  }

  return (
    <div className="h-[520px] w-full rounded-xl border border-slate-200 overflow-hidden bg-slate-50">
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
        <Background color="#e2e8f0" gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
