export function renderTruckList(list, { total, selectedId, status, ago, onSelect }) {
  const ul = document.getElementById('list');
  ul.replaceChildren();
  if (!list.length) {
    const empty = document.createElement('li');
    empty.className = 'empty';
    empty.textContent = 'Ningún camión coincide con los filtros.';
    ul.appendChild(empty);
  }
  list.forEach(truck => {
    const item = document.createElement('li');
    if (truck.id === selectedId) item.classList.add('sel');
    const button = document.createElement('button');
    button.type = 'button';
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.style.background = status[truck.status].color;
    const plate = document.createElement('span');
    plate.className = 'nm';
    plate.textContent = truck.plate;
    const speed = document.createElement('span');
    speed.className = 'sp';
    speed.textContent = truck.speed;
    const unit = document.createElement('small');
    unit.textContent = ' km/h';
    speed.appendChild(unit);
    const signal = document.createElement('span');
    signal.className = 'sb';
    signal.textContent = [truck.driver, truck.updated ? ago(truck.updated) : 'Sin señal'].filter(Boolean).join(' · ');
    const fuel = document.createElement('span');
    fuel.className = 'fu' + (truck.fuel != null && truck.fuel < 25 ? ' low' : '');
    fuel.textContent = truck.fuel != null ? `${truck.fuel}% comb.` : '—';
    button.append(dot, plate, speed, signal, fuel);
    button.onclick = () => onSelect(truck.id);
    item.appendChild(button);
    ul.appendChild(item);
  });
  document.getElementById('count').textContent = `${list.length} de ${total} camiones`;
}
