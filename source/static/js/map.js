/* ---------- Session (real auth guard) ----------
   Shared token with login.html: localStorage.itertrack_token.
   Missing token or 401 from GET /auth/me -> clear storage and go back to "/". */
import { authHeaders, clearSessionAndRedirect, verificarSesion } from './session.js';
import { getTrucks, getLocation, getHistory } from './truck-api.js';
import { getTruckList, setTrucks, getSelectedId, setSelectedId, state, getMarkers, getMoves, getRafId, setRafId } from './truck-store.js';
import { syncTrucks } from './truck-sync.js';
import { applyTelemetryPoint, buildHistory } from './truck-telemetry.js';
import { filterAndSortTrucks } from './truck-selection.js';
import { createMovementController } from './truck-movement.js';
import { renderSpeedBars, renderFleetDonuts, buildSparkline } from './truck-charts.js';
import { renderTruckList } from './truck-list.js';
import { createTruckIcon } from './truck-marker.js';
import { renderTruckDetail } from './truck-detail.js';

/* ---------- Data (real endpoints: /trucks + location polling) ---------- */
const SPEED_LIMIT = 90;      // km/h: alert threshold and chart limit
const POLL_MS = 3000;        // location refresh interval
const MOVE_MIN_MS = 400;     // movement tween floor: keeps short hops visible
const MOVE_MAX_MS = 6000;    // movement tween cap: never longer than two polls
const MOVE_EASE = k => (k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2); // easeInOutQuad
const OPEN_ZOOM = 12;         // zoom used when the map opens on the first truck
const STALE_MS = 10 * 60e3;  // no signal for 10 min -> truck considered off
const HISTORY_MAX = 18;      // speed samples kept for the detail sparkline

const STATUS = {
  move: {label:'En movimiento', color:'#5a7ee6'},
  idle: {label:'Detenido',      color:'#eeb04a'},
  stop: {label:'Apagado',       color:'#8a949c'},
  alert:{label:'Alerta',        color:'#e0675c'},
};

// Identity colour per truck: stable across reloads (keyed on the plate) so a
// truck keeps the same colour whatever its status is. The status keeps its own
// channel: the list dot, the detail panel and the pin's halo.
const TRUCK_COLORS = ['#3f6fe0','#2f9e6b','#8b5cf0','#0e93a8','#d1468f','#7a8b2e','#e0a02f','#d64545'];
const hashTexto = s => { let h = 0; for (const c of s) h = (h * 31 + c.codePointAt(0)) >>> 0; return h; };
function colorDeCamion(t){ return TRUCK_COLORS[hashTexto(String(t.plate ?? t.id)) % TRUCK_COLORS.length]; }

// Mapped from GET /trucks (id, plate). The backend does not expose
// fuel/driver/route, so those stay null/empty and render as "no data".

function setMobileView(view){
  if (!['panel','fleet','map'].includes(view)) return;
  document.body.dataset.mobileView = view;
  document.querySelectorAll('#mobile-tabs [data-mobile-view]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.mobileView === view));
  });
  if (view === 'map') requestAnimationFrame(() => map.invalidateSize());
}
document.getElementById('mobile-tabs').addEventListener('click', event => {
  const button = event.target.closest('[data-mobile-view]');
  if (button) setMobileView(button.dataset.mobileView);
});
setMobileView('map');

/* ---------- Map ---------- */
const map = L.map('map').setView([-31.9,-64.0], 7);
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/bright';
const mapContainer = document.getElementById('map');
mapContainer.classList.add('map-style-loading');
const base = L.maplibreGL({
  style: MAP_STYLE,
  attribution:'<a href="https://openfreemap.org">OpenFreeMap</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);
const mapLibreMap = base.getMaplibreMap();
const originalRoadLineColors = new Map();
let showColoredRoads = false;
function applyRoadColorMode(){
  if (!mapLibreMap.isStyleLoaded()) return;
  mapLibreMap.getStyle().layers.forEach(layer => {
    const sourceLayer = layer['source-layer'] || '';
    const isRoadLine = layer.type === 'line' &&
      sourceLayer === 'transportation' &&
      /^(highway|bridge|tunnel)-/.test(layer.id);
    if (!isRoadLine) return;
    if (!originalRoadLineColors.has(layer.id)) {
      originalRoadLineColors.set(layer.id, layer.paint?.['line-color']);
    }
    const originalColor = originalRoadLineColors.get(layer.id);
    if (originalColor === undefined) return;
    const color = showColoredRoads
      ? originalColor
      : (layer.id.endsWith('-casing') ? '#b9c1cc' : '#e2e6ec');
    mapLibreMap.setPaintProperty(layer.id, 'line-color', color);
  });
}
function neutralizeBuildings(){
  if (!mapLibreMap.isStyleLoaded()) return;
  mapLibreMap.getStyle().layers.forEach(layer => {
    const sourceLayer = layer['source-layer'] || '';
    if (layer.type === 'fill' && sourceLayer === 'building') {
      mapLibreMap.setPaintProperty(layer.id, 'fill-opacity', 0);
    } else if (layer.type === 'fill-extrusion' && sourceLayer === 'building') {
      mapLibreMap.setPaintProperty(layer.id, 'fill-extrusion-opacity', 0);
    }
  });
  applyRoadColorMode();
}
function mostrarCargaEstilo(){
  mapContainer.classList.add('map-style-loading');
}
function ocultarCargaEstilo(){
  mapContainer.classList.remove('map-style-loading');
}
function mapaListo(){
  neutralizeBuildings();
  ocultarCargaEstilo();
}
mapLibreMap.on('styledataloading', mostrarCargaEstilo);
mapLibreMap.on('load', mapaListo);
mapLibreMap.on('style.load', neutralizeBuildings);
mapLibreMap.on('error', ocultarCargaEstilo);
document.addEventListener('keydown', event => {
  const target = event.target;
  const isEditing = target instanceof HTMLElement &&
    (target.isContentEditable || ['INPUT','TEXTAREA','SELECT'].includes(target.tagName));
  if (!window.matchMedia('(min-width: 944px)').matches || isEditing ||
      event.repeat || event.ctrlKey || event.metaKey ||
      !event.altKey || !event.shiftKey || event.code !== 'KeyR') return;
  event.preventDefault();
  showColoredRoads = !showColoredRoads;
  applyRoadColorMode();
});
new ResizeObserver(() => map.invalidateSize()).observe(document.getElementById('map'));

const pinIcon = (truck, selected) => createTruckIcon(truck, selected, L);

const movementDistance = (aLat, aLng, bLat, bLng) => {
  const R = 6371e3, dLat = (bLat-aLat)*Math.PI/180, dLng = (bLng-aLng)*Math.PI/180;
  const h = Math.sin(dLat/2)**2 + Math.cos(aLat*Math.PI/180)*Math.cos(bLat*Math.PI/180)*Math.sin(dLng/2)**2;
  return 2 * R * Math.asin(Math.sqrt(h));
};
const movement = createMovementController({
  moves: getMoves(), markers: getMarkers(),
  minDuration: MOVE_MIN_MS, maxDuration: MOVE_MAX_MS,
  defaultDuration: POLL_MS, ease: MOVE_EASE, distance: movementDistance,
});
const { programarMovimiento } = movement;

/* ---------- Utilities ---------- */
const ago = ms => {
  const s = Math.max(0, Math.round((Date.now()-ms)/1000));
  if (s < 60) return `hace ${s} s`;
  if (s < 3600) return `hace ${Math.round(s/60)} min`;
  return `hace ${Math.round(s/3600)} h`;
};
const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();

function visibleTrucks(){ return filterAndSortTrucks(getTruckList(), state); }

// Geographic helpers used to derive speed/heading from real coordinates.
const toRad = d => d * Math.PI / 180;
const toDeg = r => r * 180 / Math.PI;
function haversineM(aLat, aLng, bLat, bLng){
  const R = 6371e3;
  const dLat = toRad(bLat - aLat), dLng = toRad(bLng - aLng);
  const h = Math.sin(dLat/2)**2 + Math.cos(toRad(aLat))*Math.cos(toRad(bLat))*Math.sin(dLng/2)**2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
function bearing(aLat, aLng, bLat, bLng){
  const y = Math.sin(toRad(bLng - aLng)) * Math.cos(toRad(bLat));
  const x = Math.cos(toRad(aLat)) * Math.sin(toRad(bLat)) -
            Math.sin(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.cos(toRad(bLng - aLng));
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

// Status is derived from real telemetry: fresh + fast = move/alert, fresh +
// slow = idle, stale or unknown = stop.
function estadoDe(t){
  if (!t.updated) return 'stop';
  if (Date.now() - t.updated > STALE_MS) return 'stop';
  if (t.speed > SPEED_LIMIT) return 'alert';
  if (t.speed < 3) return 'idle';
  return 'move';
}

const renderBars = list => renderSpeedBars(list, { selectedId: getSelectedId(), onSelect: id => select(id, true), speedLimit: SPEED_LIMIT });
const renderDonuts = () => renderFleetDonuts(getTruckList());
const sparkline = data => buildSparkline(data, SPEED_LIMIT);

/* ---------- Render ---------- */
function render(){
  const list = visibleTrucks();
  const ids = new Set(list.map(t=>t.id));

  getTruckList().forEach(t => {
    if (t.lat === null) return; // no location yet: nothing to pin
    let mk = getMarkers().get(t.id);
    if (!mk){
      mk = L.marker([t.lat,t.lng], {icon:pinIcon(t,false), title:t.plate});
      mk.on('click', () => select(t.id, false));
      getMarkers().set(t.id, mk);
    }
    if (!getMoves().has(t.id)) mk.setLatLng([t.lat,t.lng]); // an in-flight tween owns the pin
    mk.setIcon(pinIcon(t, t.id===getSelectedId()));
    if (ids.has(t.id)) mk.addTo(map); else map.removeLayer(mk);
  });

  renderTruckList(list, { total: getTruckList().length, selectedId: getSelectedId(), status: STATUS, ago, onSelect: id => select(id, true) });

  renderBars(list);
  renderDonuts();
  renderDetail();
}

function renderDetail(){
  renderTruckDetail(getTruckList().find(truck => truck.id === getSelectedId()), { status: STATUS, ago, sparkline });
}

function select(id, fly){
  setSelectedId(id);
  const t = getTruckList().find(x=>x.id===id);
  if (t){
    if (fly && t.lat!=null) map.flyTo([t.lat,t.lng], Math.max(map.getZoom(), 10), {duration:.8});
    cargarHistorial(t);
  }
  render();
}

/* ---------- Real API calls ---------- */
function crearEstadoCamion(t){
  return {
    id: t.id,
    plate: t.plate,
    color: colorDeCamion(t),   // identity colour, fixed for the whole session
    lat: null, lng: null,
    heading: 0,
    status: 'stop',
    speed: 0,
    fuel: null,  // not exposed by the backend
    driver: '',  // not exposed by the backend
    route: '',   // not exposed by the backend
    updated: 0,
    history: [],
  };
}
function aplicarPunto(t, p){
  applyTelemetryPoint(t, p, {
    haversineM, bearing, programarMovimiento, estadoDe, historyMax: HISTORY_MAX,
  });
}

// Poll GET /trucks/{id}/location for every truck (replaces the example's
// movement simulation with real telemetry).
async function actualizarUbicaciones(){
  await syncTrucks({ map, createTruckState: crearEstadoCamion });
  await Promise.all(getTruckList().map(async t => {
    try{
      const res = await getLocation(t.id, authHeaders());
      if (res.status === 401){ clearSessionAndRedirect(); return; }
      if (!res.ok) return; // 404: truck without registered locations
      const p = await res.json();
      aplicarPunto(t, p);
    }catch(error){
      console.error('Error al actualizar ubicación:', error);
    }
  }));
  render();
}

// GET /trucks/{id}/iter: derive a real speed history for the selected truck.
async function cargarHistorial(t){
  try{
    const res = await getHistory(t.id, authHeaders());
    if (res.status === 401){ clearSessionAndRedirect(); return; }
    if (!res.ok) return;
    const pts = await res.json();
    const hist = buildHistory(pts, { haversineM, historyMax: HISTORY_MAX });
    if (hist.length) t.history = hist;
    render();
  }catch(error){
    console.error('Error al cargar historial:', error);
  }
}

/* ---------- Events ---------- */
document.getElementById('q').oninput = e => { state.q = e.target.value; render(); };
document.getElementById('sort').onchange = e => { state.sort = e.target.value; render(); };
document.getElementById('dir').onchange  = e => { state.dir  = e.target.value; render(); };
document.getElementById('chips').addEventListener('click', e => {
  const b = e.target.closest('.chip'); if (!b) return;
  state.status = b.dataset.s;
  document.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', c===b));
  render();
});
function setView(v){
  state.view = v;
  document.querySelectorAll('#seg button').forEach(c => c.setAttribute('aria-pressed', c.dataset.v===v));
  render();
}
document.getElementById('seg').addEventListener('click', e => {
  const b = e.target.closest('button'); if (b) setView(b.dataset.v);
});
document.getElementById('alertBtn').onclick = () => setView('alert');
document.getElementById('btn-logout').addEventListener('click', clearSessionAndRedirect);

/* ---------- Boot: only with a valid session ---------- */
// Open the map on the first truck of the list, honouring the user's sort/filter.
function centrarEnPrimerCamion(){
  const t = visibleTrucks()[0];
  if (!t || t.lat === null) return;   // nothing located yet: keep the default view
  map.setView([t.lat, t.lng], Math.max(map.getZoom(), OPEN_ZOOM));
}

verificarSesion().then(async (sesionValida) => {
  if (!sesionValida) return;
  const ok = await syncTrucks({ map, createTruckState: crearEstadoCamion });
  render();
  if (!ok) return;
  await actualizarUbicaciones();
  centrarEnPrimerCamion();
  setInterval(actualizarUbicaciones, POLL_MS);
});
