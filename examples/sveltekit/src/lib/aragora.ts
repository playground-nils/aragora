/**
 * Aragora SDK Client for SvelteKit — browser-safe exports only.
 *
 * Server-side client lives in aragora.server.ts (uses $env/dynamic/private).
 */

import { createClient, type AragoraClient } from '@aragora/sdk';
import { PUBLIC_ARAGORA_API_URL } from '$env/static/public';

// Browser client (singleton)
let browserClient: AragoraClient | null = null;

export function getBrowserClient(): AragoraClient {
  if (typeof window === 'undefined') {
    throw new Error('getBrowserClient must be called in browser context');
  }

  if (!browserClient) {
    browserClient = createClient({
      baseUrl: PUBLIC_ARAGORA_API_URL || 'http://localhost:8080',
    });
  }

  return browserClient;
}

export type { Debate, Agent } from '@aragora/sdk';
