/**
 * Aragora SDK — server-side client (for SvelteKit load functions).
 *
 * This module imports $env/dynamic/private and must only be used
 * in server-side code (+page.server.ts, +layout.server.ts, hooks).
 */

import { createClient, type AragoraClient } from '@aragora/sdk';
import { env } from '$env/dynamic/private';

export function getServerClient(): AragoraClient {
  return createClient({
    baseUrl: env.ARAGORA_API_URL || 'http://localhost:8080',
    apiKey: env.ARAGORA_API_KEY,
  });
}
