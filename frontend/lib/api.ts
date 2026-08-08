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
export type TableColumn = { name: string; type: string; nullable: boolean };
export type TableFk = {
  constrained_columns: string[]; referred_table: string; referred_columns: string[];
};
export type TableSchema = {
  name: string; columns: TableColumn[]; primary_keys: string[];
  foreign_keys: TableFk[]; row_count: number;
};
export type BrowseResult = {
  columns: string[]; rows: unknown[][]; total: number; primary_keys: string[];
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
  status: () => fetch('/api/status').then(r => j<{ db_connected: boolean; dialect: string | null; tables: string[] }>(r)),
  providers: () => fetch('/api/llm/providers').then(r => j<ProviderStatus[]>(r)),
  settings: () => fetch('/api/settings').then(r => j<{ has_openrouter_api_key: boolean; openai_compat_url: string }>(r)),
  saveSecrets: (body: { openrouter_api_key?: string; openai_compat_url?: string }) =>
    post('/api/settings/secrets', body).then(r => j<{ success: boolean }>(r)),
  connect: (url: string) =>
    post('/api/db/connect', { url }).then(r => j<{ success: boolean; dialect: string; tables: string[] }>(r)),
  schema: () => fetch('/api/db/schema').then(r => j<{ tables: TableSchema[] }>(r)),
  generate: (request: string, provider: string, model: string) =>
    post('/api/query/generate', { request, provider, model }).then(r => j<GenerateResult>(r)),
  execute: (sql: string, confirm_write = false) =>
    post('/api/db/execute', { sql, confirm_write }).then(r => j<ExecResult>(r)),

  tableRows: (table: string, opts: { limit?: number; offset?: number; orderBy?: string; dir?: 'asc' | 'desc' } = {}) => {
    const q = new URLSearchParams();
    if (opts.limit) q.set('limit', String(opts.limit));
    if (opts.offset) q.set('offset', String(opts.offset));
    if (opts.orderBy) { q.set('order_by', opts.orderBy); q.set('dir', opts.dir ?? 'asc'); }
    return fetch(`/api/db/table/${encodeURIComponent(table)}/rows?${q}`).then(r => j<BrowseResult>(r));
  },
  insertRow: (table: string, values: Record<string, unknown>) =>
    post(`/api/db/table/${encodeURIComponent(table)}/rows`, { values })
      .then(r => j<{ success: boolean; pk: Record<string, unknown> }>(r)),
  updateRow: (table: string, pk: Record<string, unknown>, values: Record<string, unknown>) =>
    fetch(`/api/db/table/${encodeURIComponent(table)}/rows`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pk, values }),
    }).then(r => j<{ success: boolean; affected: number }>(r)),
  deleteRow: (table: string, pk: Record<string, unknown>) =>
    fetch(`/api/db/table/${encodeURIComponent(table)}/rows`, {
      method: 'DELETE', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pk }),
    }).then(r => j<{ success: boolean; affected: number }>(r)),
  importFile: (file: File, table: string, mode: 'create' | 'append') => {
    const fd = new FormData();
    fd.append('file', file); fd.append('table', table); fd.append('mode', mode);
    return fetch('/api/db/import', { method: 'POST', body: fd })
      .then(r => j<{ success: boolean; inserted: number; table: string }>(r));
  },
  exportUrl: (table: string, fmt: 'csv' | 'xlsx') =>
    `/api/db/table/${encodeURIComponent(table)}/export?format=${fmt}`,
  backupUrl: () => '/api/db/backup',
};
