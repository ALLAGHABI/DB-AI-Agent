export type ProviderStatus = {
  id: string; label: string; is_local: boolean; available: boolean;
  models: string[]; detail: string;
};
export type ExecResult = {
  kind: 'rows' | 'affected'; applied_sql: string;
  columns: string[]; rows: unknown[][]; affected: number;
};
export type GenerateResult = {
  sql: string; sql_class: 'read' | 'write' | 'ddl';
  provider: string; model: string; is_local: boolean;
};

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw Object.assign(new Error(
      typeof body.detail === 'string' ? body.detail : body.detail?.message ?? 'Error'
    ), { status: res.status, detail: body.detail });
  }
  return res.json();
}

const post = (url: string, body: unknown) =>
  fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const api = {
  providers: () => fetch('/api/llm/providers').then(r => j<ProviderStatus[]>(r)),
  settings: () => fetch('/api/settings').then(r => j<{ has_openrouter_api_key: boolean; openai_compat_url: string }>(r)),
  saveSecrets: (body: { openrouter_api_key?: string; openai_compat_url?: string }) =>
    post('/api/settings/secrets', body).then(r => j<{ success: boolean }>(r)),
  connect: (url: string) =>
    post('/api/db/connect', { url }).then(r => j<{ success: boolean; dialect: string; tables: string[] }>(r)),
  generate: (request: string, provider: string, model: string) =>
    post('/api/query/generate', { request, provider, model }).then(r => j<GenerateResult>(r)),
  execute: (sql: string, confirm_write = false) =>
    post('/api/db/execute', { sql, confirm_write }).then(r => j<ExecResult>(r)),
};
