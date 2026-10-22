import { Link } from 'react-router-dom';

/* T7 scaffold placeholder: the real v10 login screen is ported in T8. */
export default function LoginPage() {
  return (
    <main className="page">
      <div>
        <h1>IterTrack</h1>
        <p>Iniciar sesión — placeholder del scaffold (T7).</p>
        <p>
          ¿No tenés cuenta? <Link to="/register">Crear cuenta</Link>
        </p>
      </div>
    </main>
  );
}
