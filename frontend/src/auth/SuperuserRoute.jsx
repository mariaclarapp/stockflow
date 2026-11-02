import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./auth-context";

function SuperuserRoute() {
  const { user } = useAuth();

  if (!user?.is_superuser) {
    return <Navigate to="/admin" replace />;
  }

  return <Outlet />;
}

export default SuperuserRoute;
