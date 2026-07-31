import { NavLink, Outlet, useNavigate } from "react-router";
import { useAuth } from "../lib/auth";

const links = [
  { to: "/", label: "Resumen", icon: "⌂", end: true },
  { to: "/analyses/new", label: "Nuevo análisis", icon: "+" },
  { to: "/analyses", label: "Historial", icon: "≡" },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">BM</span>
          <div>
            <strong>BlueberryMicroID</strong>
            <small>Apoyo microbiológico</small>
          </div>
        </div>

        <nav className="main-nav" aria-label="Navegación principal">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              <span aria-hidden="true">{link.icon}</span>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-summary">
            <span className="avatar">{user?.username.slice(0, 2).toUpperCase()}</span>
            <div>
              <strong>{user?.username}</strong>
              <small>{user?.role === "admin" ? "Administrador" : "Especialista"}</small>
            </div>
          </div>
          <button className="button button-ghost button-full" onClick={handleLogout} type="button">
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="mobile-header">
          <div className="brand compact">
            <span className="brand-mark">BM</span>
            <strong>BlueberryMicroID</strong>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
