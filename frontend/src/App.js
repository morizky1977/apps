import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import AuthPage from "@/pages/AuthPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import Dashboard from "@/pages/Dashboard";
import Tasks from "@/pages/Tasks";
import Evaluation from "@/pages/Evaluation";
import AppLayout from "@/components/AppLayout";
import { Toaster } from "@/components/ui/sonner";

const Protected = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-sm text-zinc-500">Memuat…</div>;
  if (!user) return <Navigate to="/masuk" replace />;
  return children;
};

const PublicOnly = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-sm text-zinc-500">Memuat…</div>;
  if (user) return <Navigate to="/dasbor" replace />;
  return children;
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/masuk" element={<PublicOnly><AuthPage /></PublicOnly>} />
            <Route path="/lupa-sandi" element={<PublicOnly><ForgotPasswordPage /></PublicOnly>} />
            <Route element={<Protected><AppLayout /></Protected>}>
              <Route path="/" element={<Navigate to="/dasbor" replace />} />
              <Route path="/dasbor" element={<Dashboard />} />
              <Route path="/tugas" element={<Tasks />} />
              <Route path="/evaluasi" element={<Evaluation />} />
            </Route>
            <Route path="*" element={<Navigate to="/dasbor" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </div>
  );
}

export default App;
