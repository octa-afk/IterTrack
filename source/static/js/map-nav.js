// Sidebar toggle (v10 chrome): hides the rail, keeps the mini brand in the bar.
const app = document.querySelector('.app'), btn = document.getElementById('navToggle'), side = document.getElementById('sidebar');
function setNav(open){
  app.classList.toggle('nav-off', !open);
  side.inert = !open;
  btn.setAttribute('aria-expanded', open);
  btn.setAttribute('aria-label', open ? 'Ocultar panel lateral' : 'Mostrar panel lateral');
  btn.title = btn.getAttribute('aria-label');
  try{ localStorage.setItem('itertrack-nav', open ? '1' : '0'); }catch(e){}
}
btn.addEventListener('click', () => setNav(app.classList.contains('nav-off')));
try{ if(localStorage.getItem('itertrack-nav') === '0') setNav(false); }catch(e){}
