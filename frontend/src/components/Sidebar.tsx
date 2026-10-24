import { NavLink } from 'react-router-dom';
import { Mark } from './Mark';

/*
 * `to` navega; sin `to` la sección todavía no existe y se muestra deshabilitada
 * (S5). Nada de páginas vacías: el usuario ve que no está, no un placeholder.
 */
const NAV_ITEMS: {
  label: string;
  to?: string;
  icon: React.ReactNode;
}[] = [
  { label: 'Panel', to: '/map', icon: <path d="M3 11l9-8 9 8v10h-6v-6H9v6H3z" /> },
  {
    label: 'Camiones',
    to: '/fleet',
    // Camión de perfil con caja, cabina y ruedas (Lucide `truck`): sin ruedas el
    // contorno se lee como una carpeta a 21 px.
    icon: (
      <>
        <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2" />
        <path d="M15 18H9" />
        <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14" />
        <circle cx="17" cy="18" r="2" />
        <circle cx="7" cy="18" r="2" />
      </>
    ),
  },
  {
    label: 'Rutas',
    to: '/viajes',
    icon: (
      <>
        <circle cx="6" cy="19" r="2" />
        <circle cx="18" cy="5" r="2" />
        <path d="M8 19h6a4 4 0 0 0 0-8h-4a4 4 0 0 1 0-8h6" />
      </>
    ),
  },
  { label: 'Reportes', icon: <path d="M3 12h4l3-8 4 16 3-8h4" /> },
  {
    label: 'Ajustes',
    // Engranaje de ocho dientes (Lucide `settings`). El path anterior tenía la
    // geometría cruzada y a 21 px se veía como un borrón.
    icon: (
      <>
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
  },
];

export function Sidebar({ onLogout }: { onLogout: () => void }) {
  return (
    <aside className="side" id="sidebar">
      <div className="side-in">
        <div className="logo">
          <Mark />
          IterTrack
        </div>
        <nav aria-label="Principal">
          {NAV_ITEMS.map((item) =>
            item.to ? (
              <NavLink
                key={item.label}
                to={item.to}
                className={({ isActive }) => (isActive ? 'on' : undefined)}
              >
                <svg viewBox="0 0 24 24">{item.icon}</svg>
                {item.label}
              </NavLink>
            ) : (
              <a
                key={item.label}
                aria-disabled="true"
                title="Próximamente"
                className="soon"
              >
                <svg viewBox="0 0 24 24">{item.icon}</svg>
                {item.label}
              </a>
            ),
          )}
        </nav>
        <button className="logout" id="btn-logout" type="button" onClick={onLogout}>
          <svg viewBox="0 0 24 24">
            <path d="M9 21H5V3h4M16 17l5-5-5-5M21 12H9" />
          </svg>
          Salir
        </button>
      </div>
    </aside>
  );
}
