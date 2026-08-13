import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  LayoutDashboard, PlusCircle, CheckSquare, Brain,
  History, Bot, LogOut, Network, Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { adminAPI } from '@/services/api';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/tasks/new', icon: PlusCircle, label: 'New Task' },
  { to: '/approvals', icon: CheckSquare, label: 'Approvals' },
  { to: '/memory', icon: Brain, label: 'Memory' },
  { to: '/history', icon: History, label: 'History' },
  { to: '/agents', icon: Bot, label: 'Agents' },
];

interface ToastState { msg: string; loading: boolean }

function ProviderToast({ msg, loading, onDone }: ToastState & { onDone: () => void }) {
  useEffect(() => {
    if (loading) return;
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [loading, onDone]);

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="bg-slate-900 text-white text-sm px-5 py-3 rounded-xl shadow-2xl border border-slate-700 flex items-center gap-3">
        {loading
          ? <Loader2 className="w-3.5 h-3.5 text-yellow-400 animate-spin" />
          : <div className="w-2 h-2 rounded-full bg-green-400" />
        }
        {msg}
      </div>
    </div>
  );
}

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [toast, setToast] = useState<ToastState | null>(null);
  const clickCountRef = useRef(0);
  const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSecretClick = useCallback(async () => {
    clickCountRef.current += 1;

    if (clickTimerRef.current) clearTimeout(clickTimerRef.current);
    clickTimerRef.current = setTimeout(() => { clickCountRef.current = 0; }, 2000);

    if (clickCountRef.current >= 5) {
      clickCountRef.current = 0;
      if (clickTimerRef.current) clearTimeout(clickTimerRef.current);

      // Immediate feedback — don't wait for the API
      setToast({ msg: 'Switching provider...', loading: true });

      try {
        const res = await adminAPI.toggleProvider();
        const { label, model_label } = res.data;
        setToast({ msg: `Switched to ${label} — ${model_label}`, loading: false });
      } catch {
        setToast({ msg: 'Could not switch provider', loading: false });
      }
    }
  }, []);

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 text-white flex flex-col">
        <div
          className="p-4 border-b border-slate-700 cursor-default select-none"
          onClick={handleSecretClick}
        >
          <div className="flex items-center gap-2">
            <Network className="w-6 h-6 text-blue-400" />
            <div>
              <h1 className="font-bold text-sm leading-tight">Agent Orchestration</h1>
              <p className="text-xs text-slate-400">Multi-Agent Platform</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-slate-700">
          <div className="flex items-center justify-between">
            <div className="text-xs text-slate-400 truncate">{user?.email}</div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {toast && <ProviderToast {...toast} onDone={() => setToast(null)} />}
    </div>
  );
}
