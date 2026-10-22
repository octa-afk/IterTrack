/* Auth endpoints. Contract: source/services/auth.py. */
import { apiRequest } from './client';
import type { Token, UserCreate, UserResponse } from './types';

/**
 * POST /auth/login — OAuth2 Password Flow (x-www-form-urlencoded).
 * The backend expects a form body, not JSON.
 */
export function login(username: string, password: string): Promise<Token> {
  return apiRequest<Token>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  });
}

/** POST /auth/register — JSON body, returns the created user (201). */
export function register(payload: UserCreate): Promise<UserResponse> {
  return apiRequest<UserResponse>('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/** GET /auth/me — the current user for the active bearer token. */
export function me(): Promise<UserResponse> {
  return apiRequest<UserResponse>('/auth/me');
}
