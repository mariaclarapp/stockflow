import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./auth-context";

function ProtectedRoute() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <main className="session-loader" aria-live="polite">
        <span className="spinner" aria-hidden="true" />
        <p>Verificando sessão...</p>
      </main>
    );
  }

  if (!user?.is_staff) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
