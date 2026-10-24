import { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { clearToken } from '../api/client';
import { DashboardProvider } from '../state/DashboardProvider';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

const NAV_KEY = 'itertrack-nav';

/*
 * Shell de las secciones autenticadas. El provider de la flota vive acá, no en
 * cada página: cambiar de sección no reinicia el polling ni pierde la selección.
 * Cada página monta su propio `.grid` dentro de `.content`.
 */
export function DashboardLayout() {
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(() => localStorage.getItem(NAV_KEY) !== '0');

  const toggleNav = () => {
    setNavOpen((open) => {
      const next = !open;
      try {
        localStorage.setItem(NAV_KEY, next ? '1' : '0');
      } catch {
        /* localStorage unavailable: keep the in-memory state only */
      }
      return next;
    });
  };

  const handleLogout = () => {
    clearToken();
    navigate('/');
  };

  return (
    <DashboardProvider>
      <div className={navOpen ? 'app' : 'app nav-off'}>
        <Sidebar onLogout={handleLogout} />
        <div className="content">
          <Topbar navOpen={navOpen} onToggleNav={toggleNav} />
          <Outlet />
        </div>
      </div>
    </DashboardProvider>
  );
}
