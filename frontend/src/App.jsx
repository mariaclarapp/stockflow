import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import AdminLayout from "./layouts/AdminLayout";
import CompetenciasPage from "./pages/CompetenciasPage";
import DashboardPage from "./pages/DashboardPage";
import ImportacoesPage from "./pages/ImportacoesPage";
import LoginPage from "./pages/LoginPage";
import MedicamentoDetalhePage from "./pages/MedicamentoDetalhePage";
import MedicamentosPage from "./pages/MedicamentosPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="competencias" element={<CompetenciasPage />} />
          <Route path="importacoes" element={<ImportacoesPage />} />
          <Route path="medicamentos" element={<MedicamentosPage />} />
          <Route path="medicamentos/:id" element={<MedicamentoDetalhePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

export default App;
