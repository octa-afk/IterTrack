import { Link } from 'react-router-dom';

/* T7 scaffold placeholder: the real register screen is ported in T8. */
export default function RegisterPage() {
  return (
    <main className="page">
      <div>
        <h1>Crear cuenta</h1>
        <p>Registro — placeholder del scaffold (T7).</p>
        <p>
          ¿Ya tenés cuenta? <Link to="/">Iniciar sesión</Link>
        </p>
      </div>
    </main>
  );
}
