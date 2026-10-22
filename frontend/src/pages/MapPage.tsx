import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import { Topbar } from '../components/Topbar';
import { MobileTabs } from '../components/MobileTabs';
import { clearToken } from '../api/client';

const NAV_KEY = 'itertrack-nav';

/*
 * T8: the dashboard shell (sidebar, topbar, mobile tabs) ported 1:1 from the
 * vanilla map.html. The `.grid` content (map, list, detail, charts) is filled
 * in by T9-T11; for now it renders empty so the floating panel layout is visible.
 */
export default function MapPage() {
  const navigate = useNavigate();
  const [navOpen, setNavOpen] = useState(() => localStorage.getItem(NAV_KEY) !== '0');
  const [mobileView, setMobileView] = useState('map');

  useEffect(() => {
    document.body.dataset.mobileView = mobileView;
    return () => {
      delete document.body.dataset.mobileView;
    };
  }, [mobileView]);

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
    <>
      <div className={navOpen ? 'app' : 'app nav-off'}>
        <Sidebar onLogout={handleLogout} />
        <div className="content">
          <Topbar navOpen={navOpen} onToggleNav={toggleNav} avatarText="FL" />
          <div className="grid">
            <div className="col" />
            <div className="col" />
          </div>
        </div>
      </div>
      <MobileTabs view={mobileView} onChange={setMobileView} />
    </>
  );
}
