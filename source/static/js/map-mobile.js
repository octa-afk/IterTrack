const $ = s => document.querySelector(s);
const W = 2400, G = 100, LIMIT = 90, LOW_FUEL = 25;
const ST = {move:['En movimiento','var(--mv)'], idle:['Detenido','var(--id)'], stop:['Apagado','var(--st)'], alert:['Exceso de velocidad','var(--al)']};
const ICONS = {
  speed:'<path d="M12 14l4-4M3 17a9 9 0 1 1 18 0"/>',
  fuel:'<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  signal:'<path d="M2 8.5a15 15 0 0 1 20 0M5 12a10 10 0 0 1 14 0M8.5 15.5a5 5 0 0 1 7 0M12 19h.01M3 3l18 18"/>'
};
const AL_COLOR = {speed:'var(--al)', fuel:'var(--id)', signal:'var(--st)'};

/* ---------- Camiones simulados ---------- */
const NAMES = ['Martín R.','Lucía F.','Diego P.','Sofía M.','Tomás G.','Valeria C.','Nicolás A.','Camila S.'];
const trucks = NAMES.map((driver, i) => {
  const gx = 800 + Math.floor(Math.random()*12)*G, gy = 800 + Math.floor(Math.random()*12)*G;
  const base = i === 0 ? 102 : i === 6 ? 0 : i === 7 ? -1 : 35 + Math.random()*40;
  const t = {id:i, plate:`${String.fromCharCode(65+i)}${String.fromCharCode(70+i)} ${100+i*137} ${String.fromCharCode(75+i)}${String.fromCharCode(66+i)}`,
    driver, x:gx, y:gy, dx:i%2?1:0, dy:i%2?0:1, base, kmh:Math.max(0,base), ph:Math.random()*6, fuel:i===3?18:40+i*7, hist:[], al:[]};
  t.tx = gx + t.dx*G; t.ty = gy + t.dy*G;
  return t;
});
const status = t => t.base < 0 ? 'stop' : t.kmh > LIMIT ? 'alert' : t.kmh > 2 ? 'move' : 'idle';
const ago = ms => { const s = Math.max(0, Math.round(ms/1000)); return s < 60 ? `hace ${s} s` : `hace ${Math.round(s/60)} min`; };
function nextTarget(t){
  const dirs = [[1,0],[-1,0],[0,1],[0,-1]].filter(d => !(d[0] === -t.dx && d[1] === -t.dy));
  let d = Math.random() < .6 ? [t.dx, t.dy] : dirs[Math.floor(Math.random()*dirs.length)];
  const nx = t.x + d[0]*G, ny = t.y + d[1]*G;
  if (nx < 400 || nx > 2000 || ny < 400 || ny > 2000) d = [-t.dx, -t.dy];
  t.dx = d[0]; t.dy = d[1]; t.tx = t.x + d[0]*G; t.ty = t.y + d[1]*G;
}

/* ---------- Alertas derivadas de los datos ---------- */
const since = new Map();   // clave -> instante en que empezó la alerta
function alertsOf(t){
  const out = [];
  if (t.base >= 0 && t.kmh > LIMIT) out.push({type:'speed', title:'Exceso de velocidad', detail:`${Math.round(t.kmh)} km/h · límite ${LIMIT}`});
  if (t.fuel < LOW_FUEL) out.push({type:'fuel', title:'Combustible bajo', detail:`${t.fuel}% restante`});
  if (t.base < 0) out.push({type:'signal', title:'Sin señal', detail:'Camión apagado o sin GPS'});
  out.forEach(a => {
    a.key = `${a.type}-${t.id}`; a.t = t;
    if (!since.has(a.key)) since.set(a.key, Date.now() - (120 + Math.random()*2400)*1000);
    a.since = since.get(a.key);
  });
  [...since.keys()].filter(k => k.endsWith('-' + t.id) && !out.some(a => a.key === k)).forEach(k => since.delete(k));
  return out;
}
const RANK = {speed:0, fuel:1, signal:2};

/* ---------- Mapa genérico (pestaña secundaria) ---------- */
(function(){
  let s = `<svg width="${W}" height="${W}" viewBox="0 0 ${W} ${W}"><rect width="${W}" height="${W}" fill="var(--bg)"/>`;
  [[610,810,280,180],[1210,1010,380,180],[1010,1410,180,280],[1610,610,180,280],[810,1610,380,180]].forEach(p => s += `<rect x="${p[0]}" y="${p[1]}" width="${p[2]}" height="${p[3]}" rx="18" fill="var(--park)"/>`);
  s += `<path d="M0 1850C500 1650 1000 2050 1500 1800S2200 1700 2400 1750" fill="none" stroke="var(--water)" stroke-width="90"/>`;
  for (let i = 0; i <= W; i += G) s += `<path d="M${i} 0V${W}M0 ${i}H${W}" stroke="var(--road)" stroke-width="7"/>`;
  for (let i = 0; i <= W; i += 400) s += `<path d="M${i} 0V${W}M0 ${i}H${W}" stroke="var(--roadb)" stroke-width="24"/><path d="M${i} 0V${W}M0 ${i}H${W}" stroke="var(--road)" stroke-width="17"/>`;
  $('#world').innerHTML = s + '</svg>';
})();
const view = {x:0, y:0, k:1}, world = $('#world'), mapEl = $('#map');
const paintView = () => world.style.transform = `translate(${view.x}px,${view.y}px) scale(${view.k})`;
function zoomAt(cx, cy, f){
  const nk = Math.min(2.5, Math.max(.45, view.k*f)), r = nk/view.k;
  view.x = cx - (cx - view.x)*r; view.y = cy - (cy - view.y)*r; view.k = nk; paintView();
}
view.x = innerWidth/2 - 1200; view.y = innerHeight*.4 - 1200; paintView();
let anim = null;
function flyTo(x, y){
  const sx = innerWidth/2, sy = (innerHeight - 190)/2, x0 = view.x, y0 = view.y, x1 = sx - x*view.k, y1 = sy - y*view.k, t0 = performance.now();
  cancelAnimationFrame(anim);
  (function step(now){
    const k = Math.min(1, (now - t0)/600), e = 1 - Math.pow(1-k, 3);
    view.x = x0 + (x1-x0)*e; view.y = y0 + (y1-y0)*e; paintView();
    if (k < 1) anim = requestAnimationFrame(step);
  })(t0);
}
const ptrs = new Map(); let moved = 0, mapSel = null;
mapEl.addEventListener('pointerdown', e => { cancelAnimationFrame(anim); ptrs.set(e.pointerId, [e.clientX, e.clientY]); moved = 0; });
mapEl.addEventListener('pointermove', e => {
  const p = ptrs.get(e.pointerId); if (!p) return;
  if (ptrs.size === 1){ view.x += e.clientX - p[0]; view.y += e.clientY - p[1]; moved += Math.abs(e.clientX - p[0]) + Math.abs(e.clientY - p[1]); paintView(); }
  else if (ptrs.size === 2){
    const o = [...ptrs.entries()].find(([id]) => id !== e.pointerId)[1];
    const d0 = Math.hypot(p[0]-o[0], p[1]-o[1]), d1 = Math.hypot(e.clientX-o[0], e.clientY-o[1]);
    moved += 10; if (d0 > 0) zoomAt((e.clientX+o[0])/2, (e.clientY+o[1])/2, d1/d0);
  }
  ptrs.set(e.pointerId, [e.clientX, e.clientY]);
});
function upPtr(e){
  const was = ptrs.size === 1 && ptrs.has(e.pointerId);
  ptrs.delete(e.pointerId);
  if (was && moved < 8 && e.type === 'pointerup'){
    const pin = e.target.closest('.pin');
    if (pin) mapSelect(+pin.dataset.id); else mapSelect(null);
  }
}
mapEl.addEventListener('pointerup', upPtr); mapEl.addEventListener('pointercancel', upPtr);
mapEl.addEventListener('wheel', e => { e.preventDefault(); zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1.12 : .89); }, {passive:false});
$('#zi').onclick = () => zoomAt(innerWidth/2, innerHeight/2, 1.4);
$('#zo').onclick = () => zoomAt(innerWidth/2, innerHeight/2, 1/1.4);
function mapSelect(id){
  mapSel = id;
  trucks.forEach(t => t.pin.classList.toggle('sel', t.id === id));
  $('#mini').hidden = id === null;
  if (id !== null){ flyTo(trucks[id].x, trucks[id].y); updateMini(); }
}
function updateMini(){
  const t = trucks[mapSel]; if (!t) return;
  const s = status(t);
  $('#mPlate').textContent = t.plate; $('#mSt').textContent = ST[s][0]; $('#mSt').style.color = ST[s][1];
  $('#mSp').textContent = Math.round(Math.max(0, t.kmh)); $('#mFu').textContent = t.fuel + '%'; $('#mDr').textContent = t.driver;
}
$('#mMore').onclick = () => openDetail(mapSel);

/* ---------- Elementos fijos (se crean una vez y se actualizan en sitio) ---------- */
trucks.forEach(t => {
  const p = document.createElement('div');
  p.className = 'pin'; p.dataset.id = t.id; p.innerHTML = '<svg viewBox="0 0 512 512"><use href="#trk"/></svg>';
  world.appendChild(p); t.pin = p;
  const li = document.createElement('li');
  li.innerHTML = '<button type="button"><span class="dot"></span><b class="nm"></b><span class="sp"></span><span class="sb"></span><span class="fu"></span></button>';
  li.querySelector('.nm').textContent = t.plate;
  li.firstChild.onclick = () => openDetail(t.id);
  $('#list').appendChild(li); t.li = li;
});
const bars = $('#bars');
bars.innerHTML = `<div class="lim"><span>Límite ${LIMIT} km/h</span></div>`;
trucks.forEach(t => {
  const b = document.createElement('button');
  b.className = 'bar'; b.type = 'button'; b.setAttribute('aria-label', t.plate);
  const p = t.plate.replace(/ /g, '');
  b.innerHTML = `<i></i><b>${p.slice(0,2)}${p.slice(-2)}</b>`;
  b.onclick = () => openDetail(t.id);
  bars.appendChild(b); t.bar = b;
});
const BAR_H = 150 - 18, BAR_MAX = 120;
bars.querySelector('.lim').style.bottom = (18 + BAR_H*LIMIT/BAR_MAX) + 'px';

/* ---------- Filtros de la lista ---------- */
const st = {f:'all', q:'', view:'all'};
const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
function visible(t){
  const s = status(t);
  return (st.view === 'all' || t.al.length > 0) &&
    (st.f === 'all' || st.f === s || (st.f === 'move' && s === 'alert')) &&
    (!st.q || norm(t.plate + ' ' + t.driver).includes(norm(st.q)));
}
function setChip(f){ st.f = f; document.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', c.dataset.s === f)); }
function setView(v){ st.view = v; document.querySelectorAll('#seg button').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === v)); }
$('#chips').onclick = e => { const b = e.target.closest('.chip'); if (b){ setChip(b.dataset.s); refresh(); } };
$('#seg').onclick = e => { const b = e.target.closest('button'); if (b){ setView(b.dataset.v); refresh(); } };
$('#q').oninput = e => { st.q = e.target.value; refresh(); };
$('#q').onkeydown = e => { if (e.key === 'Enter') e.target.blur(); };
$('#tiles').onclick = e => {
  const b = e.target.closest('.tile'); if (!b) return;
  if (b.dataset.v){ setView('alert'); setChip('all'); } else { setView('all'); setChip(b.dataset.s); }
  refresh(); setTab('fleet');
};

/* ---------- Alertas en el panel (con actualización por claves) ---------- */
const alEls = new Map();
function syncAlerts(list){
  const box = $('#alerts');
  const keys = new Set(list.map(a => a.key));
  alEls.forEach((el, k) => { if (!keys.has(k)){ el.remove(); alEls.delete(k); } });
  list.forEach((a, i) => {
    let el = alEls.get(a.key);
    if (!el){
      el = document.createElement('button');
      el.type = 'button'; el.className = 'al'; el.style.setProperty('--c', AL_COLOR[a.type]);
      el.innerHTML = `<span class="ic"><svg viewBox="0 0 24 24">${ICONS[a.type]}</svg></span><b></b><span class="ago"></span><small></small><em></em>`;
      el.querySelector('b').textContent = a.title;
      el.querySelector('small').textContent = `${a.t.plate} · ${a.t.driver}`;
      el.onclick = () => openDetail(a.t.id);
      alEls.set(a.key, el);
    }
    el.querySelector('em').textContent = a.detail;
    el.querySelector('.ago').textContent = ago(Date.now() - a.since);
    if (box.children[i] !== el) box.insertBefore(el, box.children[i] || null);
  });
  let ok = $('#noal');
  if (!list.length && !ok){
    ok = document.createElement('div');
    ok.id = 'noal'; ok.className = 'card ok';
    ok.innerHTML = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/></svg><div><b>Todo en orden</b>No hay alertas activas.</div>';
    box.appendChild(ok);
  } else if (list.length && ok) ok.remove();
}

/* ---------- Refresco general ---------- */
function refresh(){
  let n = 0, mv = 0, idle = 0, stop = 0, withAl = 0, sum = 0, sumN = 0;
  const all = [];
  trucks.forEach(t => {
    t.al = alertsOf(t); all.push(...t.al);
    const s = status(t), v = visible(t);
    if (s === 'move' || s === 'alert') mv++; else if (s === 'idle') idle++; else stop++;
    if (t.al.length) withAl++;
    if (t.base >= 0){ sum += t.kmh; sumN++; }
    if (v) n++;
    t.li.hidden = !v;
    t.li.querySelector('.dot').style.setProperty('--c', ST[s][1]);
    t.li.querySelector('.sp').innerHTML = `${Math.round(Math.max(0, t.kmh))} <small>km/h</small>`;
    t.li.querySelector('.sb').textContent = `${t.driver} · ${s === 'alert' ? 'Alerta' : ST[s][0]}`;
    const fu = t.li.querySelector('.fu'); fu.textContent = `${t.fuel}% comb.`; fu.classList.toggle('low', t.fuel < LOW_FUEL);
    t.pin.style.setProperty('--c', ST[s][1]);
    const bi = t.bar.querySelector('i');
    bi.style.height = Math.max(4, BAR_H*Math.max(0, t.kmh)/BAR_MAX) + 'px';
    t.bar.classList.toggle('over', s === 'alert');
  });
  $('#tot').textContent = trucks.length;
  $('#nMove').textContent = mv; $('#nIdle').textContent = idle; $('#nStop').textContent = stop; $('#nAlert').textContent = withAl;
  $('#avg').textContent = `Media ${sumN ? Math.round(sum/sumN) : 0} km/h`;
  $('#count').textContent = `${n} de ${trucks.length} camiones`;
  $('#empty').hidden = n > 0;
  const tg = $('#alTag'); tg.textContent = all.length; tg.classList.toggle('red', all.length > 0);
  const bd = $('#badge'); bd.hidden = !all.length; bd.textContent = all.length;
  all.sort((a, b) => RANK[a.type] - RANK[b.type] || a.since - b.since);
  syncAlerts(all);
  if (mapSel !== null) updateMini();
  if (detailId !== null) updateDetail();
}

/* ---------- Detalle de camión ---------- */
let detailId = null;
const heading = t => Math.round((Math.atan2(t.dx, -t.dy)*180/Math.PI + 360) % 360);
function openDetail(id){
  const t = trucks[id]; detailId = id;
  $('#dPlate').textContent = t.plate;
  $('#dSub').textContent = `${t.driver} · Ruta ${t.id + 1}`;
  $('#dbody').innerHTML = `
  <div class="card"><div class="hero"><div><b id="dSp"></b> <small>km/h</small></div><span id="dSt" style="font-weight:600;font-size:13px"></span></div>
    <div class="st3"><div><b>${t.fuel}%</b><span>Combustible</span></div><div><b id="dHd"></b><span>Rumbo</span></div><div><b id="dAgo"></b><span>Señal</span></div></div></div>
  <div class="sec"><h2>Alertas del camión</h2></div>
  <div class="card" id="dAl"></div>
  <div class="sec"><h2>Velocidad reciente</h2></div>
  <div class="card"><svg class="spark" viewBox="0 0 300 64" preserveAspectRatio="none" aria-label="Velocidad reciente"><line id="dLim" x1="0" x2="300" stroke="#eeb04a" stroke-dasharray="4 4" stroke-width="1"/><path id="dPath" fill="none" stroke="#5a7ee6" stroke-width="2" vector-effect="non-scaling-stroke"/></svg></div>
  <div class="sec"><h2>Información</h2></div>
  <div class="card"><dl><dt>Chofer</dt><dd>${t.driver}</dd><dt>Ruta</dt><dd>Ruta ${t.id + 1}</dd><dt>Posición</dt><dd id="dPos"></dd></dl></div>
  <button class="btn" id="dMap" type="button" style="margin-top:16px">Ver en el mapa</button>`;
  $('#dMap').onclick = () => { closeDetail(); setTab('map'); mapSelect(id); };
  $('#detail').scrollTop = 0;
  document.body.classList.add('dopen'); $('#detail').inert = false;
  updateDetail();
}
function closeDetail(){ detailId = null; document.body.classList.remove('dopen'); $('#detail').inert = true; }
function updateDetail(){
  const t = trucks[detailId]; if (!t) return;
  const s = status(t);
  $('#dSp').textContent = Math.round(Math.max(0, t.kmh));
  $('#dSt').textContent = ST[s][0]; $('#dSt').style.color = ST[s][1];
  $('#dHd').textContent = heading(t) + '°';
  $('#dAgo').textContent = t.base < 0 ? 'Sin señal' : 'Activa';
  $('#dPos').textContent = `${(-31.9 - (t.y - 1200)/20000).toFixed(3)}, ${(-64 + (t.x - 1200)/20000).toFixed(3)}`;
  $('#dAl').innerHTML = t.al.length
    ? t.al.map(a => `<div class="dal" style="--c:${AL_COLOR[a.type]}"><i></i><span><b style="font-weight:600">${a.title}</b> · ${a.detail}</span></div>`).join('')
    : '<span style="color:var(--muted)">Sin alertas activas.</span>';
  const h = t.hist; if (h.length < 2) return;
  const w = 300, ht = 64, max = Math.max(120, ...h), y = v => ht - 4 - (ht - 10)*v/max;
  let d = `M0,${y(h[0])}`;
  for (let i = 1; i < h.length; i++){ const x0 = (i-1)*w/(h.length-1), x1 = i*w/(h.length-1), cx = (x0+x1)/2; d += ` C${cx},${y(h[i-1])} ${cx},${y(h[i])} ${x1},${y(h[i])}`; }
  $('#dPath').setAttribute('d', d); $('#dLim').setAttribute('y1', y(LIMIT)); $('#dLim').setAttribute('y2', y(LIMIT));
}
$('#dback').onclick = closeDetail;
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

/* ---------- Pestañas ---------- */
function setTab(t){
  document.body.dataset.tab = t;
  document.querySelectorAll('#tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.t === t));
}
$('#tabs').onclick = e => { const b = e.target.closest('button'); if (b){ closeDetail(); setTab(b.dataset.t); } };

/* ---------- Simulación ---------- */
let last = performance.now(), tick = 0;
(function loop(now){
  const dt = Math.min(.1, (now - last)/1000); last = now; tick += dt;
  trucks.forEach(t => {
    if (t.base >= 0){
      t.kmh = t.base === 0 ? 0 : Math.max(5, t.base + Math.sin(tick*.6 + t.ph)*8);
      let step = t.kmh*.5*dt;
      while (step > 0){
        const dist = Math.hypot(t.tx - t.x, t.ty - t.y);
        if (dist <= step){ step -= dist; t.x = t.tx; t.y = t.ty; nextTarget(t); }
        else { t.x += (t.tx - t.x)/dist*step; t.y += (t.ty - t.y)/dist*step; step = 0; }
      }
    } else t.kmh = 0;
    t.pin.style.transform = `translate(${t.x}px,${t.y}px) translate(-50%,-50%) scale(${1/Math.max(.6, view.k)})`;
  });
  requestAnimationFrame(loop);
})(last);
setInterval(refresh, 500);
setInterval(() => trucks.forEach(t => { t.hist.push(Math.round(t.kmh)); if (t.hist.length > 18) t.hist.shift(); }), 1000);
refresh();
