import { Route, Routes } from 'react-router-dom';
import { DashboardLayout } from './components/DashboardLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import MapPage from './pages/MapPage';
import FleetPage from './pages/FleetPage';
import TripsPage from './pages/TripsPage';

/*
 * Rutas espejo de los handlers de FastAPI (`source/main.py`): cada una
 * devuelve `index.html` y React Router resuelve el resto. Camiones vive en
 * `/fleet` porque `GET /trucks` ya es el endpoint JSON, y Rutas en `/viajes`
 * porque `GET /trips` es la API de viajes.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<DashboardLayout />}>
        <Route path="/map" element={<MapPage />} />
        <Route path="/fleet" element={<FleetPage />} />
        <Route path="/viajes" element={<TripsPage />} />
      </Route>
    </Routes>
  );
}
