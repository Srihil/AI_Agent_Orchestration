import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { workflowAPI } from '@/services/api';
import {
  PlusCircle, Search, BarChart2, PenTool, ClipboardCheck,
  Network, Zap, ShieldCheck, Loader2,
} from 'lucide-react';

const EXAMPLE_TASKS = [
  'Research the latest developments in AI and large language models',
  'Analyze the pros and cons of microservices vs monolithic architecture',
  'Compare the top programming languages for machine learning tasks',
  'Research recent advances in quantum computing and summarize findings',
];

const PIPELINE = [
  { icon: Network,        label: 'Supervisor',  desc: 'Routes your task to the right agents' },
  { icon: Search,         label: 'Researcher',  desc: 'Searches the web for current information' },
  { icon: BarChart2,      label: 'Analyst',     desc: 'Structures and analyses the findings' },
  { icon: PenTool,        label: 'Writer',      desc: 'Produces the final response' },
  { icon: ClipboardCheck, label: 'Reviewer',    desc: 'Checks quality before delivery' },
];

export function NewTaskPage() {
  const [task, setTask] = useState('');
  const [requireApproval, setRequireApproval] = useState(false);
  const [maxSteps, setMaxSteps] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!task.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await workflowAPI.create(task.trim(), requireApproval, maxSteps);
      navigate(`/workflows/${res.data.id}`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || 'Failed to create workflow');
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 bg-blue-100 rounded-xl">
          <PlusCircle className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">New Task</h1>
          <p className="text-slate-500 text-sm">Describe a complex task for the agent pipeline</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Textarea */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            className="w-full px-4 pt-4 pb-2 text-sm text-slate-800 placeholder:text-slate-400 resize-none focus:outline-none"
            rows={5}
            placeholder="Describe the complex task you want the agents to handle..."
            required
          />
          <div className="px-4 pb-3 flex items-center justify-between border-t border-slate-50 pt-2">
            <span className="text-xs text-slate-400">Be specific — more detail leads to better results</span>
            <span className={`text-xs ${task.length > 0 ? 'text-slate-400' : 'text-slate-200'}`}>
              {task.length}
            </span>
          </div>
        </div>

        {/* Example tasks */}
        <div>
          <p className="text-xs font-medium text-slate-400 mb-2">Quick examples</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {EXAMPLE_TASKS.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setTask(ex)}
                className="text-left text-xs text-slate-600 bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 hover:border-blue-200 px-3 py-2.5 rounded-lg transition-colors leading-relaxed"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Options */}
        <div className="grid grid-cols-2 gap-4">
          {/* Max Steps */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-slate-700">Max Steps</span>
              <span className="text-xl font-bold text-blue-600">{maxSteps}</span>
            </div>
            <input
              type="range"
              min={5}
              max={50}
              step={5}
              value={maxSteps}
              onChange={(e) => setMaxSteps(parseInt(e.target.value))}
              className="w-full accent-blue-600 cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-300 mt-1.5">
              <span>5</span>
              <span>50</span>
            </div>
          </div>

          {/* Require Approval */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex flex-col">
            <span className="text-sm font-medium text-slate-700 mb-3">Require Approval</span>
            <button
              type="button"
              onClick={() => setRequireApproval(!requireApproval)}
              className={`flex-1 rounded-lg border text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                requireApproval
                  ? 'bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
              }`}
            >
              {requireApproval
                ? <><ShieldCheck className="w-4 h-4" /> Pause for review</>
                : <><Zap className="w-4 h-4" /> Auto-deliver</>
              }
            </button>
            <p className="text-xs text-slate-400 mt-2 text-center">
              {requireApproval ? 'You approve before final output' : 'Agents deliver automatically'}
            </p>
          </div>
        </div>

        {/* Pipeline preview */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
          <p className="text-xs font-medium text-slate-500 mb-3">Agent pipeline</p>
          <div className="flex items-center gap-1 flex-wrap">
            {PIPELINE.map(({ icon: Icon, label }, i) => (
              <div key={label} className="flex items-center gap-1">
                <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5">
                  <Icon className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs text-slate-600 font-medium">{label}</span>
                </div>
                {i < PIPELINE.length - 1 && (
                  <div className="w-4 h-px bg-slate-200 flex-shrink-0" />
                )}
              </div>
            ))}
            {requireApproval && (
              <>
                <div className="w-4 h-px bg-orange-200 flex-shrink-0" />
                <div className="flex items-center gap-1.5 bg-orange-50 border border-orange-200 rounded-lg px-2.5 py-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-orange-500" />
                  <span className="text-xs text-orange-700 font-medium">Approval</span>
                </div>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 rounded-lg p-3 border border-red-100">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !task.trim()}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2 shadow-sm"
        >
          {loading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Starting workflow...</>
          ) : (
            'Start Workflow'
          )}
        </button>
      </form>
    </div>
  );
}
