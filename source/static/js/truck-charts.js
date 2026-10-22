export function renderFleetDonuts(trucks) {
  const n = trucks.length || 1;
  const moving = trucks.filter(t => t.status === 'move' || t.status === 'alert').length;
  const fresh = trucks.filter(t => t.updated && Date.now() - t.updated < 5 * 60e3).length;
  const donut = (pct, color, label, value, center) => {
    const r = 27, circumference = 2 * Math.PI * r;
    const pctText = center === undefined ? Math.round(pct) + '%' : center;
    return `<div class="dn"><div style="position:relative"><svg viewBox="0 0 68 68"><circle cx="34" cy="34" r="${r}" stroke="#e9ebe8"/><circle cx="34" cy="34" r="${r}" stroke="${color}" stroke-linecap="round" stroke-dasharray="${circumference * pct / 100} ${circumference}"/></svg><div class="pc" style="color:${color}">${pctText}</div></div><div class="t">${label}<b>${value}</b></div></div>`;
  };
  document.getElementById('donuts').innerHTML =
    donut(moving / n * 100, '#eeb04a', 'En ruta', `${moving} de ${n}`) +
    donut(0, '#9a8fd6', 'Combustible', 'promedio', '—') +
    donut(fresh / n * 100, '#7fa0e8', 'Con señal', `${fresh} de ${n}`);
}

export function renderSpeedBars(list, { selectedId, onSelect, speedLimit }) {
  const max = 120, height = 129 - 18;
  const bars = document.getElementById('bars');
  bars.replaceChildren();
  const limit = document.createElement('div');
  limit.className = 'limit';
  limit.style.bottom = (18 + height * speedLimit / max) + 'px';
  const label = document.createElement('span');
  label.textContent = `Límite ${speedLimit} km/h`;
  limit.appendChild(label);
  bars.appendChild(limit);
  list.forEach(truck => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'bar ' + (truck.id === selectedId ? 'sel' : '');
    button.dataset.id = truck.id;
    button.title = `${truck.plate}: ${truck.speed} km/h`;
    const bar = document.createElement('i');
    bar.style.height = Math.max(3.5, height * truck.speed / max) + 'px';
    const plate = document.createElement('b');
    plate.textContent = String(truck.plate).slice(0, 2) + String(truck.plate).slice(-2);
    button.append(bar, plate);
    button.onclick = () => onSelect(Number(button.dataset.id));
    bars.appendChild(button);
  });
}

export function buildSparkline(data, speedLimit) {
  const width = 300, height = 64, max = Math.max(120, ...data);
  const points = data.map((value, index) => [index * (width / (data.length - 1)), height - 4 - (height - 10) * value / max]);
  let path = `M${points[0][0]},${points[0][1]}`;
  for (let i = 1; i < points.length; i++) {
    const [x0, y0] = points[i - 1], [x1, y1] = points[i], center = (x0 + x1) / 2;
    path += ` C${center},${y0} ${center},${y1} ${x1},${y1}`;
  }
  const limitY = height - 4 - (height - 10) * speedLimit / max;
  return `<svg class="spark" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-label="Velocidad reciente"><line x1="0" y1="${limitY}" x2="${width}" y2="${limitY}" stroke="#eeb04a" stroke-dasharray="4 4" stroke-width="1"/><path d="${path}" fill="none" stroke="#5a7ee6" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>`;
}
