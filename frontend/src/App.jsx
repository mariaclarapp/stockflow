import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import AdminLayout from "./layouts/AdminLayout";
import CompetenciasPage from "./pages/CompetenciasPage";
import DashboardPage from "./pages/DashboardPage";
import ImportacoesPage from "./pages/ImportacoesPage";
import LoginPage from "./pages/LoginPage";
import MedicamentoDetalhePage from "./pages/MedicamentoDetalhePage";
import MedicamentosCompararPage from "./pages/MedicamentosCompararPage";
import MedicamentosPage from "./pages/MedicamentosPage";
import PublicMedicamentosPage from "./pages/PublicMedicamentosPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/medicamentos" replace />} />
      <Route path="/medicamentos" element={<PublicMedicamentosPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="competencias" element={<CompetenciasPage />} />
          <Route path="importacoes" element={<ImportacoesPage />} />
          <Route path="medicamentos" element={<MedicamentosPage />} />
          <Route path="medicamentos/comparar" element={<MedicamentosCompararPage />} />
          <Route path="medicamentos/:id" element={<MedicamentoDetalhePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/medicamentos" replace />} />
    </Routes>
  );
}

export default App;
