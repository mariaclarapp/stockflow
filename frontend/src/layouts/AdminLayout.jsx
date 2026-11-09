import { useState } from "react";
import {
  BarChart3,
  Boxes,
  CalendarDays,
  KeyRound,
  FileUp,
  LayoutDashboard,
  LogOut,
  Menu,
  Pill,
  SearchCheck,
  UsersRound,
  X,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/auth-context";
import { Brand } from "../components/Brand";
import PasswordChangeCard from "../components/PasswordChangeCard";

const navItems = [
  { label: "Visão geral", icon: LayoutDashboard, to: "/admin", end: true },
  { label: "Importações", icon: FileUp, to: "/admin/importacoes" },
  { label: "Medicamentos", icon: Pill, to: "/admin/medicamentos" },
  { label: "Análise", icon: BarChart3, to: "/admin/analises" },
  { label: "Competências", icon: CalendarDays, to: "/admin/competencias" },
  { label: "Validação", icon: SearchCheck, to: "/admin/validacao" },
  { label: "Funcionários", icon: UsersRound, to: "/admin/funcionarios", superuserOnly: true },
];

function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const [isPasswordCardOpen, setIsPasswordCardOpen] = useState(false);
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
          {navItems.filter((item) => !item.superuserOnly || user.is_superuser).map(({ label, icon: Icon, to, end }) =>
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
          <button
            type="button"
            className={`user-summary user-summary-button${isAccountMenuOpen ? " user-summary-button--open" : ""}`}
            onClick={() => setIsAccountMenuOpen((open) => !open)}
            aria-expanded={isAccountMenuOpen}
            aria-haspopup="menu"
          >
            <span className="user-avatar" aria-hidden="true">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{user.username}</strong>
              <small>Usuário administrativo</small>
            </span>
          </button>
          {isAccountMenuOpen && <div className="user-account-menu" role="menu">
            <button type="button" role="menuitem" onClick={() => { setIsAccountMenuOpen(false); setIsPasswordCardOpen(true); }}><KeyRound size={16} />Redefinir senha</button>
          </div>}
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
      {isPasswordCardOpen && <div className="account-password-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setIsPasswordCardOpen(false); }}>
        <div className="account-password-dialog" role="dialog" aria-modal="true" aria-labelledby="password-title">
          <PasswordChangeCard onClose={() => setIsPasswordCardOpen(false)} />
        </div>
      </div>}
    </div>
  );
}

export default AdminLayout;
