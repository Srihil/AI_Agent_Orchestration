import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { workflowAPI } from '@/services/api';
import { Network } from 'lucide-react';

const EXAMPLE_TASKS = [
  'Research the current state of quantum computing and prepare a structured report',
  'Analyze the pros and cons of microservices vs monolithic architecture',
  'Research recent advances in large language models and summarize key findings',
  'Compare the top 5 programming languages for machine learning in 2024',
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
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">New Task</h1>
        <p className="text-slate-500 text-sm mt-1">
          Describe a complex task and let the agent orchestration system handle it.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-6 space-y-5">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Task Description</label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={4}
              placeholder="Describe the complex task you want the agents to handle..."
              required
            />
          </div>

          <div>
            <p className="text-xs text-slate-500 mb-2">Examples:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_TASKS.map((ex) => (
                <button
                  key={ex}
                  type="button"
                  onClick={() => setTask(ex)}
                  className="text-xs text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-100 px-2.5 py-1 rounded-full transition-colors"
                >
                  {ex.substring(0, 50)}...
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Max Steps</label>
              <input
                type="number"
                min={5}
                max={50}
                value={maxSteps}
                onChange={(e) => setMaxSteps(parseInt(e.target.value))}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-400 mt-1">Max agent routing steps (5–50)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Require Approval</label>
              <label className="flex items-center gap-3 mt-2 cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={requireApproval}
                    onChange={(e) => setRequireApproval(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setRequireApproval(!requireApproval)}
                    className={`w-10 h-6 rounded-full transition-colors cursor-pointer ${requireApproval ? 'bg-blue-600' : 'bg-slate-200'}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full shadow mt-1 transition-transform ${requireApproval ? 'translate-x-5 ml-0' : 'translate-x-1'}`} />
                  </div>
                </div>
                <span className="text-sm text-slate-600">
                  {requireApproval ? 'Yes — pause before delivery' : 'No — auto-deliver'}
                </span>
              </label>
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</div>
          )}

          <div className="bg-slate-50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Network className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium text-slate-700">What will happen</span>
            </div>
            <div className="text-xs text-slate-500 space-y-1">
              <p>1. Supervisor analyzes your task and routes to specialized agents</p>
              <p>2. Researcher gathers information using search tools</p>
              <p>3. Analyst processes and structures the findings</p>
              <p>4. Writer produces a comprehensive response</p>
              <p>5. Reviewer checks quality before delivery</p>
              {requireApproval && <p>6. <strong>You approve before final delivery</strong></p>}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !task.trim()}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Starting workflow...' : 'Start Workflow'}
          </button>
        </form>
      </div>
    </div>
  );
}
