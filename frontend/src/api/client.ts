/*
 * Thin fetch wrapper shared by the typed API modules.
 *
 * It mirrors the vanilla `source/static/js/session.js` token handling (same
 * `localStorage` key) but stays framework-agnostic: it never redirects or
 * mutates the session on its own. Callers decide what to do with an error,
 * which keeps an expected 401 from a failed login from bouncing the user.
 */

export const TOKEN_KEY = 'itertrack_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function readDetail(res: Response): Promise<unknown> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    return body.detail ?? body;
  } catch {
    return undefined;
  }
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (detail === undefined || detail === null) return fallback;
  return JSON.stringify(detail);
}

/**
 * Perform an authenticated JSON request.
 *
 * - Adds `Authorization: Bearer <token>` (unless the caller overrides it).
 * - Throws `ApiError` for any non-2xx response, preserving the API `detail`.
 * - Returns `undefined` for `204 No Content`.
 */
export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  for (const [name, value] of Object.entries(authHeaders())) {
    if (!headers.has(name)) headers.set(name, value);
  }

  const res = await fetch(path, { ...init, headers });

  if (!res.ok) {
    const detail = await readDetail(res);
    throw new ApiError(
      res.status,
      detailMessage(detail, `HTTP ${res.status}`),
      detail,
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}
