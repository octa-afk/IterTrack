const TABS = [
  { view: 'panel', label: 'Panel' },
  { view: 'fleet', label: 'Flota' },
  { view: 'map', label: 'Mapa' },
];

interface MobileTabsProps {
  view: string;
  onChange: (view: string) => void;
}

export function MobileTabs({ view, onChange }: MobileTabsProps) {
  return (
    <nav className="mobile-tabs" id="mobile-tabs" aria-label="Vistas móviles">
      {TABS.map((tab) => (
        <button
          key={tab.view}
          type="button"
          data-mobile-view={tab.view}
          aria-pressed={view === tab.view}
          onClick={() => onChange(tab.view)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
