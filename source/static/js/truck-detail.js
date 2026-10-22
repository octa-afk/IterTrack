export function renderTruckDetail(truck, { status, ago, sparkline }) {
  const element = document.getElementById('detail');
  if (!truck) {
    const empty = document.createElement('div');
    empty.className = 'noSel';
    empty.textContent = 'Elegí un camión en el mapa o en la lista para ver su detalle.';
    element.replaceChildren(empty);
    return;
  }
  element.replaceChildren();
  const when = document.createElement('div'); when.className = 'when';
  const left = document.createElement('span');
  const plate = document.createElement('b'); plate.style.color = 'var(--ink)'; plate.style.fontSize = '14px'; plate.textContent = truck.plate;
  const label = document.createElement('span'); label.style.color = status[truck.status].color; label.style.fontWeight = '600'; label.textContent = status[truck.status].label;
  left.append(plate, document.createTextNode(' · '), label);
  const right = document.createElement('span'); right.textContent = truck.updated ? ago(truck.updated) : 'Sin señal'; when.append(left, right);
  const stats = document.createElement('div'); stats.className = 'st';
  const cell = (value, text) => { const node = document.createElement('div'); const bold = document.createElement('b'); bold.textContent = value; const caption = document.createElement('span'); caption.textContent = text; node.append(bold, caption); return node; };
  stats.append(cell(truck.speed, 'km/h'), cell(truck.fuel != null ? `${truck.fuel}%` : '—', 'Combustible'), cell(`${Math.round(truck.heading)}°`, 'Rumbo'));
  const info = document.createElement('dl'); info.className = 'info';
  const row = (term, value) => { const dt = document.createElement('dt'); dt.textContent = term; const dd = document.createElement('dd'); dd.textContent = value; info.append(dt, dd); };
  row('Chofer', truck.driver || '—'); row('Ruta', truck.route || '—'); row('Posición', truck.lat != null ? `${truck.lat.toFixed(3)}, ${truck.lng.toFixed(3)}` : '—');
  element.append(when, stats, info);
  if (truck.history && truck.history.length > 1) element.insertAdjacentHTML('beforeend', sparkline(truck.history));
}
