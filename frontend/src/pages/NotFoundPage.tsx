import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <p className="text-8xl font-bold text-slate-100 select-none">404</p>
      <h1 className="text-xl font-semibold text-slate-800 mt-4">Page not found</h1>
      <p className="text-slate-400 text-sm mt-2 max-w-xs">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link
        to="/"
        className="mt-6 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
