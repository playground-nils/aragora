/**
 * Settlements Namespace API
 *
 * Provides methods for managing debate claim settlements.
 */

interface SettlementsClientInterface {
  request<T = unknown>(method: string, path: string, options?: Record<string, unknown>): Promise<T>;
}

export class SettlementsAPI {
  constructor(private client: SettlementsClientInterface) {}

  /** List pending settlements. */
  async listPending(params?: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.client.request('GET', '/api/v1/settlements', { params });
  }

  /** Get settlement history. */
  async getHistory(params?: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.client.request('GET', '/api/v1/settlements/history', { params });
  }

  /** Get settlement summary statistics. */
  async getSummary(): Promise<Record<string, unknown>> {
    return this.client.request('GET', '/api/v1/settlements/summary');
  }

  /** Get a settlement by ID. */
  async get(settlementId: string): Promise<Record<string, unknown>> {
    return this.client.request('GET', `/api/v1/settlements/${encodeURIComponent(settlementId)}`);
  }

  /** Get accuracy statistics for an agent. */
  async getAgentAccuracy(agent: string): Promise<Record<string, unknown>> {
    return this.client.request(
      'GET',
      `/api/v1/settlements/agent/${encodeURIComponent(agent)}/accuracy`
    );
  }

  /** Submit a settlement outcome. */
  async settle(
    settlementId: string,
    body: Record<string, unknown>
  ): Promise<Record<string, unknown>> {
    return this.client.request('POST', `/api/v1/settlements/${encodeURIComponent(settlementId)}/settle`, {
      body,
    });
  }

  /** Settle multiple claims in one request. */
  async settleBatch(body: Record<string, unknown>): Promise<Record<string, unknown>> {
    return this.client.request('POST', '/api/v1/settlements/batch', { body });
  }
}
