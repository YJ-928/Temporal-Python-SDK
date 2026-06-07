const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface CatalogAgent {
  id: string;
  name: string;
  url: string;
  description: string;
  request_schema?: Record<string, string>;
}

export interface CatalogOperation {
  id: string;
  name: string;
  url: string;
  description: string;
}

async function fetchJson<T>(path: string): Promise<T[]> {
  try {
    const res = await fetch(`${API_BASE_URL}${path}`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export const catalogApi = {
  getAgents: (): Promise<CatalogAgent[]> => fetchJson('/api/v1/catalog/agents'),
  getOperations: (): Promise<CatalogOperation[]> => fetchJson('/api/v1/catalog/operations'),
};
