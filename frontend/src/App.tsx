import { Route, Routes } from 'react-router-dom';
import { DashboardLayout } from './components/DashboardLayout';
import { MobileLayout } from './mobile/MobileLayout';
import { useMediaQuery } from './mobile/useMediaQuery';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import MapPage from './pages/MapPage';
import FleetPage from './pages/FleetPage';
import TripsPage from './pages/TripsPage';
import MobileMapPage from './mobile/MobileMapPage';
import MobileFleetPage from './mobile/MobileFleetPage';
import MobileTripsPage from './mobile/MobileTripsPage';

/*
 * Rutas espejo de los handlers de FastAPI (`source/main.py`): cada una
 * devuelve `index.html` y React Router resuelve el resto. Camiones vive en
 * `/fleet` porque `GET /trucks` ya es el endpoint JSON, y Rutas en `/viajes`
 * porque `GET /trips` es la API de viajes.
 *
 * Debajo de 640 px monta el shell móvil con las pantallas del diseño de
 * `extras/mobile/itertrack`; por encima, el dashboard de escritorio intacto.
 * El corte es el mismo que fija `tests/test_static_css.py`.
 */
export default function App() {
  const mobile = useMediaQuery('(max-width: 640px)');

  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      {mobile ? (
        <Route element={<MobileLayout />}>
          <Route path="/map" element={<MobileMapPage />} />
          <Route path="/fleet" element={<MobileFleetPage />} />
          <Route path="/viajes" element={<MobileTripsPage />} />
        </Route>
      ) : (
        <Route element={<DashboardLayout />}>
          <Route path="/map" element={<MapPage />} />
          <Route path="/fleet" element={<FleetPage />} />
          <Route path="/viajes" element={<TripsPage />} />
        </Route>
      )}
    </Routes>
  );
}
