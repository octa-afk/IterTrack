const TOKEN_KEY = 'itertrack_token';

function authHeaders(){
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: 'Bearer ' + token } : {};
}

// Logout (and auth failures): clear localStorage, then redirect to the login page.
function clearSessionAndRedirect(){
  localStorage.clear();
  window.location.replace('/');
}

async function verificarSesion(){
  if (!localStorage.getItem(TOKEN_KEY)){
    clearSessionAndRedirect();
    return false;
  }
  try{
    const res = await fetch('/auth/me', { headers: authHeaders() });
    if (res.ok){
      const user = await res.json();
      // Avatar initials from the real user; textContent, never innerHTML (XSS)
      document.querySelector('.avatar').textContent = String(user.username || '??').slice(0, 2).toUpperCase();
      return true;
    }
  } catch (error){
    console.error('Error al validar la sesión:', error);
  }
  // Missing token, 401 or network failure: clear storage and go back to "/"
  clearSessionAndRedirect();
  return false;
}


export { TOKEN_KEY, authHeaders, clearSessionAndRedirect, verificarSesion };
