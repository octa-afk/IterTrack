const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

export function filterAndSortTrucks(trucks, state) {
  const query = normalize(state.q.trim());
  const list = trucks.filter(truck =>
    (state.view === 'all' || truck.status === 'alert') &&
    (state.status === 'all' || truck.status === state.status) &&
    (!query || normalize(`${truck.plate} ${truck.driver} ${truck.route}`).includes(query))
  );
  const multiplier = state.dir === 'asc' ? 1 : -1;
  list.sort((a, b) => {
    const left = a[state.sort], right = b[state.sort];
    return (typeof left === 'string' ? left.localeCompare(right, 'es') : left - right) * multiplier;
  });
  return list;
}
