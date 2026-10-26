import { NavLink, useNavigate } from 'react-router-dom';
import { Mark } from '../components/Mark';
import { useDashboard } from '../state/useDashboard';
import { Icon } from './icons';

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
}

const NAV = [
  { to: '/map', icon: 'home', label: 'Panel' },
  { to: '/fleet', icon: 'truck', label: 'Camiones' },
  { to: '/viajes', icon: 'route', label: 'Rutas' },
] as const;

/*
 * Drawer del diseño móvil: navegación principal, alertas y sesión. Reusa el
 * mismo `userInitials` del contexto que el topbar de escritorio y `setFilter`
 * para que "Alertas" abra la flota ya filtrada por estado de alerta.
 */
export function MobileDrawer({ open, onClose, onLogout }: MobileDrawerProps) {
  const { trucks, userInitials, setFilter } = useDashboard();
  const navigate = useNavigate();
  const alerts = trucks.filter((truck) => truck.status === 'alert').length;

  const verAlertas = () => {
    setFilter({ view: 'alert', status: 'all' });
    onClose();
    navigate('/fleet');
  };

  return (
    <>
      <div
        className={`m-scrim${open ? ' m-scrim--on' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <nav
        className={`m-drawer${open ? ' m-drawer--on' : ''}`}
        aria-label="Menú principal"
        aria-hidden={!open}
        inert={!open}
      >
        <div className="m-drawer__head">
          <div className="m-brand">
            <Mark decorative />
            IterTrack
          </div>
          <button
            className="m-btn-ghost m-btn-ghost--fill"
            type="button"
            onClick={onClose}
            aria-label="Cerrar menú"
          >
            <Icon name="close" size={20} />
          </button>
        </div>

        <div className="m-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) => (isActive ? 'm-on' : undefined)}
            >
              <Icon name={item.icon} size={22} stroke={1.8} />
              {item.label}
            </NavLink>
          ))}
          <a className="m-soon" aria-disabled="true" title="Próximamente">
            <Icon name="report" size={22} stroke={1.8} />
            Reportes
          </a>
          <a className="m-soon" aria-disabled="true" title="Próximamente">
            <Icon name="settings" size={22} stroke={1.8} />
            Ajustes
          </a>
        </div>

        <button className="m-nav__alerts" type="button" onClick={verAlertas}>
          <span>
            <Icon name="bell" size={22} stroke={1.8} />
            Alertas
          </span>
          <small>{alerts} alertas</small>
        </button>

        <div className="m-drawer__user">
          <span className="m-avatar">{userInitials}</span>
          <span>Mi cuenta</span>
          <button className="m-logout" type="button" onClick={onLogout}>
            <Icon name="logout" size={18} />
            Salir
          </button>
        </div>
      </nav>
    </>
  );
}
