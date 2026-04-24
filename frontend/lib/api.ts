/**
 * SchemaGuard API Client
 * 
 * All calls proxy through Next.js rewrites → FastAPI at :8000.
 */

const BASE = '/api';

async function request<T = any>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request('/health'),
  dashboard: () => request('/dashboard'),
  rules: (domain?: string) => request(`/rules${domain ? `?domain=${domain}` : ''}`),
  examples: (domain?: string, category?: string) => {
    const p = new URLSearchParams();
    if (domain) p.set('domain', domain);
    if (category) p.set('category', category);
    const q = p.toString();
    return request(`/examples${q ? `?${q}` : ''}`);
  },
  auditLogs: (limit = 50, domain?: string, decision?: string) => {
    const p = new URLSearchParams({ limit: String(limit) });
    if (domain) p.set('domain', domain);
    if (decision) p.set('decision', decision);
    return request(`/audit-logs?${p.toString()}`);
  },
  violations: (limit = 50, ruleId?: string) => {
    const p = new URLSearchParams({ limit: String(limit) });
    if (ruleId) p.set('rule_id', ruleId);
    return request(`/violations?${p.toString()}`);
  },
  validate: (domain: string, record: object) =>
    request('/validate', { method: 'POST', body: JSON.stringify({ domain, record }) }),
  batchValidate: (domain: string, records: object[]) =>
    request('/batch-validate', { method: 'POST', body: JSON.stringify({ domain, records }) }),
  suggestFix: (domain: string, record: object, record_id?: string) =>
    request('/suggest/suggest-fix', { method: 'POST', body: JSON.stringify({ domain, record, record_id }) }),
  suggestRules: () =>
    request('/suggest/suggest-fix/rules'),
};
