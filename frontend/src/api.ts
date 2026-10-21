export const TOKEN_KEY = 'itertrack_token'

export async function readError(response: Response, fallback: string): Promise<never> {
  let detail = ''
  try {
    const data = await response.json() as { detail?: unknown }
    detail = data.detail ? String(data.detail) : ''
  } catch {
    // The API may return a non-JSON gateway error.
  }
  throw new Error(detail || fallback)
}

export async function login(username: string, password: string) {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  })
  if (!response.ok) await readError(response, 'No pudimos iniciar sesión. Probá de nuevo.')
  const data = await response.json() as { access_token: string }
  localStorage.setItem(TOKEN_KEY, data.access_token)
}

export async function register(payload: Record<string, string>) {
  const response = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) await readError(response, 'No se pudo crear la cuenta. Intenta de nuevo más tarde.')
  await login(payload.username, payload.password)
}
