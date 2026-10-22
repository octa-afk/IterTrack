import { Mark } from './Mark';

interface TopbarProps {
  navOpen: boolean;
  onToggleNav: () => void;
  avatarText: string;
}

export function Topbar({ navOpen, onToggleNav, avatarText }: TopbarProps) {
  const toggleLabel = navOpen ? 'Ocultar panel lateral' : 'Mostrar panel lateral';

  return (
    <div className="top">
      <div className="tl">
        <button
          className="navtoggle"
          id="navToggle"
          type="button"
          aria-controls="sidebar"
          aria-expanded={navOpen}
          aria-label={toggleLabel}
          title={toggleLabel}
          onClick={onToggleNav}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="3" />
            <path d="M9 4v16" />
          </svg>
        </button>
        <span className="minibrand">
          <Mark decorative />
          IterTrack
        </span>
        <label className="search">
          <input
            id="q"
            type="search"
            placeholder="Buscar patente, chofer o ruta"
            aria-label="Buscar camiones"
          />
          <svg viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
        </label>
      </div>
      <div className="pill">
        <button className="al" id="alertBtn" type="button">
          0 alertas
        </button>
        <svg className="bell" viewBox="0 0 24 24">
          <path d="M12 2a6 6 0 0 0-6 6v4l-2 3v1h16v-1l-2-3V8a6 6 0 0 0-6-6zm-2 18a2 2 0 0 0 4 0z" />
        </svg>
        <div className="avatar">{avatarText}</div>
      </div>
    </div>
  );
}
