import { Mark } from './Mark';

const NAV_ITEMS = [
  { label: 'Panel', active: true, icon: <path d="M3 11l9-8 9 8v10h-6v-6H9v6H3z" /> },
  { label: 'Camiones', icon: <path d="M3 7h11v9H3zM14 10h4l3 3v3h-7" /> },
  {
    label: 'Rutas',
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
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7 7 0 0 0-2-1.2L14 3h-4l-.4 2.6a7 7 0 0 0-2 1.2l-2.4-1-2 3.4-2 1.6a7 7 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7 7 0 0 0 2 1.2L10 21h4l.4-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.1-.4.2-.8.2-1.2z" />
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
          {NAV_ITEMS.map((item) => (
            <a key={item.label} className={item.active ? 'on' : undefined} tabIndex={0}>
              <svg viewBox="0 0 24 24">{item.icon}</svg>
              {item.label}
            </a>
          ))}
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
