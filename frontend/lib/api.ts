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

/** خطأ يحمل رمزاً قابلاً للترجمة بدل نص جاهز بلغة واحدة. */
export class ApiError extends Error {
  code: string;
  params: Record<string, string>;
  status: number;
  detail: unknown;

  constructor(code: string, params: Record<string, string> = {}, status = 0, detail?: unknown) {
    super(code);
    this.code = code;
    this.params = params;
    this.status = status;
    this.detail = detail;
  }
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    if (detail && typeof detail === 'object' && 'code' in detail) {
      throw new ApiError(detail.code as string,
        (detail.params ?? {}) as Record<string, string>, res.status, detail);
    }
    // FastAPI validation errors أو أي رد غير متوقع
    throw new ApiError('generic', { detail: typeof detail === 'string' ? detail : res.statusText },
      res.status, detail);
  }
  return res.json();
}

const request = async (url: string, init?: RequestInit) => {
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiError('network');
  }
};

const post = (url: string, body: unknown) =>
  request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const api = {
  status: () => request('/api/status').then(r => j<{ db_connected: boolean; dialect: string | null; tables: string[] }>(r)),
  providers: () => request('/api/llm/providers').then(r => j<ProviderStatus[]>(r)),
  settings: () => request('/api/settings').then(r => j<{ has_openrouter_api_key: boolean; openai_compat_url: string }>(r)),
  saveSecrets: (body: { openrouter_api_key?: string; openai_compat_url?: string }) =>
    post('/api/settings/secrets', body).then(r => j<{ success: boolean }>(r)),
  connect: (url: string) =>
    post('/api/db/connect', { url }).then(r => j<{ success: boolean; dialect: string; tables: string[] }>(r)),
  schema: () => request('/api/db/schema').then(r => j<{ tables: TableSchema[] }>(r)),
  generate: (nlRequest: string, provider: string, model: string) =>
    post('/api/query/generate', { request: nlRequest, provider, model }).then(r => j<GenerateResult>(r)),
  execute: (sql: string, confirm_write = false,
            meta: { source?: 'editor' | 'nl'; request?: string; model?: string } = {}) =>
    post('/api/db/execute', { sql, confirm_write, ...meta }).then(r => j<ExecResult>(r)),

  tableRows: (table: string, opts: { limit?: number; offset?: number; orderBy?: string; dir?: 'asc' | 'desc' } = {}) => {
    const q = new URLSearchParams();
    if (opts.limit) q.set('limit', String(opts.limit));
    if (opts.offset) q.set('offset', String(opts.offset));
    if (opts.orderBy) { q.set('order_by', opts.orderBy); q.set('dir', opts.dir ?? 'asc'); }
    return request(`/api/db/table/${encodeURIComponent(table)}/rows?${q}`).then(r => j<BrowseResult>(r));
  },
  insertRow: (table: string, values: Record<string, unknown>) =>
    post(`/api/db/table/${encodeURIComponent(table)}/rows`, { values })
      .then(r => j<{ success: boolean; pk: Record<string, unknown> }>(r)),
  updateRow: (table: string, pk: Record<string, unknown>, values: Record<string, unknown>) =>
    request(`/api/db/table/${encodeURIComponent(table)}/rows`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pk, values }),
    }).then(r => j<{ success: boolean; affected: number }>(r)),
  deleteRow: (table: string, pk: Record<string, unknown>) =>
    request(`/api/db/table/${encodeURIComponent(table)}/rows`, {
      method: 'DELETE', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pk }),
    }).then(r => j<{ success: boolean; affected: number }>(r)),
  importFile: (file: File, table: string, mode: 'create' | 'append') => {
    const fd = new FormData();
    fd.append('file', file); fd.append('table', table); fd.append('mode', mode);
    return request('/api/db/import', { method: 'POST', body: fd })
      .then(r => j<{ success: boolean; inserted: number; table: string }>(r));
  },
  exportUrl: (table: string, fmt: 'csv' | 'xlsx') =>
    `/api/db/table/${encodeURIComponent(table)}/export?format=${fmt}`,
  backupUrl: () => '/api/db/backup',

  reportAnalyze: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/api/reports/analyze', { method: 'POST', body: fd })
      .then(r => j<{ token: string; profile: ReportProfile }>(r));
  },
  reportGenerate: (body: {
    token: string; title: string; template: string; language: string;
    provider: string; model: string;
  }) => post('/api/reports/generate', body).then(r => j<ReportMeta>(r)),
  reportsList: () => request('/api/reports').then(r => j<ReportMeta[]>(r)),
  reportDelete: (id: string) =>
    request(`/api/reports/${id}`, { method: 'DELETE' }).then(r => j<{ success: boolean }>(r)),
  reportFileUrl: (id: string, kind: 'html' | 'pdf' | 'xlsx') => `/api/reports/${id}/${kind}`,
  reportAnalyzeTable: (table: string) =>
    post('/api/reports/analyze-table', { table })
      .then(r => j<{ token: string; profile: ReportProfile }>(r)),

  historyList: (favoritesOnly = false, limit = 50) =>
    request(`/api/history?limit=${limit}&favorites_only=${favoritesOnly}`)
      .then(r => j<HistoryEntry[]>(r)),
  historyFavorite: (id: number, favorite: boolean) =>
    request(`/api/history/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ favorite }),
    }).then(r => j<{ success: boolean }>(r)),
  historyDelete: (id: number) =>
    request(`/api/history/${id}`, { method: 'DELETE' }).then(r => j<{ success: boolean }>(r)),
  historyClear: () =>
    request('/api/history', { method: 'DELETE' })
      .then(r => j<{ success: boolean; removed: number }>(r)),

  connectionsList: () => request('/api/connections').then(r => j<SavedConnection[]>(r)),
  connectionAdd: (body: Omit<SavedConnection, 'id' | 'has_password'> & { password?: string }) =>
    post('/api/connections', body).then(r => j<SavedConnection>(r)),
  connectionDelete: (id: string) =>
    request(`/api/connections/${id}`, { method: 'DELETE' }).then(r => j<{ success: boolean }>(r)),
  connectionUse: (id: string) =>
    post(`/api/connections/${id}/connect`, {})
      .then(r => j<{ success: boolean; dialect: string; tables: string[] }>(r)),
};

export type HistoryEntry = {
  id: number; request: string | null; sql: string; sql_class: string;
  source: string; model: string | null; rows: number; success: boolean;
  created_at: string; favorite: boolean;
};
export type SavedConnection = {
  id: string; name: string; type: string; sqlite_file: string; host: string;
  port: string; database: string; username: string; has_password: boolean;
};

export type ReportProfile = {
  overview: { rows: number; cols: number; missing_pct: number; duplicate_rows: number; memory_kb: number };
  columns: { name: string; kind: string; nulls: number; unique: number }[];
  correlations: { a: string; b: string; r: number }[];
  charts: { type: string; title: string }[];
};
export type ReportMeta = {
  id: string; title: string; template: string; language: string;
  source_name: string; model_label: string; created_at: string; created_iso?: string;
  is_local: boolean; rows: number; cols: number; pdf: boolean;
};
