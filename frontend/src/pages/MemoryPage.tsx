import { useState, useEffect } from 'react';
import { memoryAPI } from '@/services/api';
import type { Memory } from '@/types';
import { formatDate } from '@/lib/utils';
import { Plus, Trash2, Edit2, Check, X, Brain } from 'lucide-react';

const MEMORY_TYPES = ['fact', 'preference', 'outcome'] as const;

export function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [filter, setFilter] = useState('all');
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState<'fact' | 'preference' | 'outcome'>('preference');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [editType, setEditType] = useState('fact');
  const [creating, setCreating] = useState(false);

  const fetchMemories = async () => {
    try {
      const res = await memoryAPI.list(filter);
      setMemories(res.data);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchMemories(); }, [filter]);

  const handleCreate = async () => {
    if (!newContent.trim()) return;
    setCreating(true);
    try {
      await memoryAPI.create(newContent.trim(), newType);
      setNewContent('');
      await fetchMemories();
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this memory?')) return;
    await memoryAPI.delete(id);
    await fetchMemories();
  };

  const startEdit = (memory: Memory) => {
    setEditingId(memory.id);
    setEditContent(memory.content);
    setEditType(memory.memory_type);
  };

  const saveEdit = async (id: string) => {
    await memoryAPI.update(id, editContent, editType);
    setEditingId(null);
    await fetchMemories();
  };

  const typeColor: Record<string, string> = {
    preference: 'bg-blue-50 text-blue-700 border-blue-200',
    outcome: 'bg-green-50 text-green-700 border-green-200',
    fact: 'bg-slate-50 text-slate-700 border-slate-200',
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Memory</h1>
        <p className="text-slate-500 text-sm mt-1">
          Long-term memory retrieved by agents to inform their responses
        </p>
      </div>

      {/* Create new memory */}
      <div className="bg-white rounded-xl border border-slate-100 shadow-sm p-5 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Brain className="w-4 h-4 text-blue-500" />
          <h2 className="font-medium text-slate-800">Add Memory</h2>
        </div>
        <textarea
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="e.g. I prefer reports in bullet-point format with concise language"
          className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          rows={3}
        />
        <div className="flex gap-3 items-center">
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value as typeof newType)}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {MEMORY_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={handleCreate}
            disabled={creating || !newContent.trim()}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            Save Memory
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {['all', ...MEMORY_TYPES].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-sm px-3 py-1.5 rounded-lg transition-colors capitalize ${
              filter === f ? 'bg-blue-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:border-blue-300'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Memory list */}
      {memories.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-100">
          <Brain className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-400 text-sm">No memories yet. Add one above to get started.</p>
        </div>
      )}

      <div className="space-y-3">
        {memories.map((memory) => (
          <div key={memory.id} className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
            {editingId === memory.id ? (
              <div className="space-y-3">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  rows={3}
                />
                <div className="flex gap-2">
                  <select
                    value={editType}
                    onChange={(e) => setEditType(e.target.value)}
                    className="border border-slate-200 rounded-lg px-3 py-2 text-sm"
                  >
                    {MEMORY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                  <button onClick={() => saveEdit(memory.id)} className="p-2 bg-green-600 hover:bg-green-700 text-white rounded-lg">
                    <Check className="w-4 h-4" />
                  </button>
                  <button onClick={() => setEditingId(null)} className="p-2 bg-slate-200 hover:bg-slate-300 rounded-lg">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="text-sm text-slate-700">{memory.content}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${typeColor[memory.memory_type] || typeColor.fact}`}>
                      {memory.memory_type}
                    </span>
                    <span className="text-xs text-slate-400">{formatDate(memory.updated_at)}</span>
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button onClick={() => startEdit(memory)} className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(memory.id)} className="p-1.5 hover:bg-red-50 rounded-lg text-slate-400 hover:text-red-500">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
