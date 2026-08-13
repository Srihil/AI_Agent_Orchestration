import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    pending: 'text-yellow-500',
    running: 'text-blue-500',
    paused: 'text-orange-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
    success: 'text-green-500',
    error: 'text-red-500',
    info: 'text-slate-400',
    pass: 'text-green-500',
    fail: 'text-red-500',
    approved: 'text-green-500',
    rejected: 'text-red-500',
  };
  return map[status] || 'text-slate-400';
}

export function statusBg(status: string): string {
  const map: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    running: 'bg-blue-100 text-blue-800 border-blue-200',
    paused: 'bg-orange-100 text-orange-800 border-orange-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    failed: 'bg-red-100 text-red-800 border-red-200',
    approved: 'bg-green-100 text-green-800 border-green-200',
    rejected: 'bg-red-100 text-red-800 border-red-200',
    success: 'bg-green-100 text-green-800 border-green-200',
    pass: 'bg-green-100 text-green-800 border-green-200',
    fail: 'bg-red-100 text-red-800 border-red-200',
  };
  return map[status] || 'bg-slate-100 text-slate-800 border-slate-200';
}
