/* Public client configuration. Contract: GET /config in source/main.py. */
import { apiRequest } from './client';
import type { ClientConfig } from './types';

/** GET /config — unauthenticated, read by the login page before anyone enters. */
export function getConfig(): Promise<ClientConfig> {
  return apiRequest<ClientConfig>('/config');
}
