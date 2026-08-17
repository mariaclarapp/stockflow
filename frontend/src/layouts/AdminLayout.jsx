import { useState } from "react";
import {
  BarChart3,
  Boxes,
  CalendarDays,
  FileUp,
  LayoutDashboard,
  LogOut,
  Menu,
  Pill,
  Settings,
  X,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/auth-context";
import { Brand } from "../components/Brand";

const navItems = [
  { label: "Visão geral", icon: LayoutDashboard, to: "/admin", end: true },
  { label: "Importações", icon: FileUp, to: "/admin/importacoes" },
  { label: "Medicamentos", icon: Pill, to: "/admin/medicamentos" },
  { label: "Competências", icon: CalendarDays },
  { label: "Análises", icon: BarChart3 },
  { label: "Configurações", icon: Settings },
];

function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  async function handleLogout() {
    setLogoutError("");
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch {
      setLogoutError("Não foi possível encerrar a sessão.");
    }
  }

  return (
    <div className="admin-shell">
      {isSidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          onClick={() => setIsSidebarOpen(false)}
          aria-label="Fechar menu"
        />
      )}

      <aside className={`sidebar${isSidebarOpen ? " sidebar--open" : ""}`}>
        <div className="sidebar__header">
          <Brand />
          <button
            type="button"
            className="icon-button sidebar__close"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Fechar menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar__nav" aria-label="Navegação administrativa">
          {navItems.map(({ label, icon: Icon, to, end }) =>
            to ? (
              <NavLink
                key={label}
                to={to}
                end={end}
                onClick={() => setIsSidebarOpen(false)}
                className={({ isActive }) =>
                  `nav-item${isActive ? " nav-item--active" : ""}`
                }
              >
                <Icon size={18} />
                <span>{label}</span>
              </NavLink>
            ) : (
              <button key={label} type="button" className="nav-item" disabled>
                <Icon size={18} />
                <span>{label}</span>
              </button>
            ),
          )}
        </nav>

        <div className="sidebar__footer">
          <div className="user-summary">
            <span className="user-avatar" aria-hidden="true">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{user.username}</strong>
              <small>Usuário administrativo</small>
            </span>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={handleLogout}
            title="Sair"
            aria-label="Sair"
          >
            <LogOut size={18} />
          </button>
          {logoutError && <p className="sidebar-error">{logoutError}</p>}
        </div>
      </aside>

      <div className="admin-content">
        <header className="mobile-header">
          <button
            type="button"
            className="icon-button"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Abrir menu"
          >
            <Menu size={21} />
          </button>
          <Brand compact />
          <Boxes size={20} aria-hidden="true" />
        </header>
        <Outlet />
      </div>
    </div>
  );
}

export default AdminLayout;
