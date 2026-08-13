import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext, useAuthProvider } from '@/hooks/useAuth';
import { Layout } from '@/components/Layout';
import { LoginPage } from '@/pages/LoginPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { NewTaskPage } from '@/pages/NewTaskPage';
import { WorkflowDetailPage } from '@/pages/WorkflowDetailPage';
import { ApprovalsPage } from '@/pages/ApprovalsPage';
import { MemoryPage } from '@/pages/MemoryPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { AgentsPage } from '@/pages/AgentsPage';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const auth = useAuthProvider();

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<DashboardPage />} />
            <Route path="tasks/new" element={<NewTaskPage />} />
            <Route path="workflows/:id" element={<WorkflowDetailPage />} />
            <Route path="approvals" element={<ApprovalsPage />} />
            <Route path="memory" element={<MemoryPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="agents" element={<AgentsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
