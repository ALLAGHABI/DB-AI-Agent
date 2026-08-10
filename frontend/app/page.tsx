'use client';
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ConnectionsPanel } from '@/components/connections-panel';
import { ErDiagram } from '@/components/er-diagram';
import { HistoryPanel } from '@/components/history-panel';
import { ModeSwitch, type AppMode } from '@/components/mode-switch';
import { ProvidersPanel, type ModelSelection } from '@/components/providers-panel';
import { QueryWorkspace } from '@/components/query-workspace';
import { ReportsStudio } from '@/components/reports-studio';
import { Shell } from '@/components/shell';
import { SqlEditor } from '@/components/sql-editor';
import { TablesBrowser } from '@/components/tables-browser';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, type HistoryEntry } from '@/lib/api';

export default function Home() {
  const t = useTranslations('nav');
  const [tables, setTables] = useState<string[]>([]);
  const [dialect, setDialect] = useState<string | null>(null);
  const [selection, setSelection] = useState<ModelSelection | null>(null);
  const onModelChange = useCallback((s: ModelSelection | null) => setSelection(s), []);

  const [apiDown, setApiDown] = useState(false);
  const [mode, setMode] = useState<AppMode>('database');
  const [tab, setTab] = useState('query');
  const [reuse, setReuse] = useState<{ request?: string; sql?: string } | null>(null);
  const [reportTable, setReportTable] = useState<string | undefined>();

  // الوضع المفضل: ?mode=reports في الرابط، وإلا آخر وضع استُخدم
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get('mode');
    const fromCookie = document.cookie.match(/(?:^|; )mode=(database|reports)/)?.[1];
    const initial = (fromUrl === 'reports' || fromUrl === 'database'
      ? fromUrl : fromCookie) as AppMode | undefined;
    if (initial) setMode(initial);
  }, []);

  const changeMode = useCallback((m: AppMode) => {
    setMode(m);
    document.cookie = `mode=${m};path=/;max-age=31536000`;
  }, []);

  const syncStatus = useCallback(async () => {
    try {
      const s = await api.status();
      setApiDown(false);
      setTables(s.db_connected ? s.tables : []);
      setDialect(s.dialect);
    } catch {
      setApiDown(true);
    }
  }, []);

  // استعادة حالة الاتصال بعد إعادة تحميل الصفحة
  useEffect(() => { syncStatus(); }, [syncStatus]);

  const onConnected = useCallback((tbs: string[]) => {
    setTables(tbs);
    syncStatus();
  }, [syncStatus]);

  const onReuse = useCallback((entry: HistoryEntry) => {
    setReuse(entry.request ? { request: entry.request } : { sql: entry.sql });
    setTab('query');
  }, []);

  // الجسر بين الوضعين: تقرير من جدول متصل
  const onReportFromTable = useCallback((table: string) => {
    setReportTable(table);
    changeMode('reports');
  }, [changeMode]);

  const connected = tables.length > 0;

  return (
    <Shell connected={connected} apiDown={apiDown}
      showStatus={mode === 'database'}
      modeSwitch={<ModeSwitch mode={mode} onChange={changeMode} />}
      sidebar={mode === 'database' ? (
        <>
          <ConnectionsPanel onConnected={onConnected} />
          <ProvidersPanel onModelChange={onModelChange} />
        </>
      ) : (
        <ProvidersPanel onModelChange={onModelChange} />
      )}
      main={mode === 'database' ? (
        <Tabs value={tab} onValueChange={v => v && setTab(v)}>
          <TabsList className="mb-2">
            <TabsTrigger value="query">{t('query')}</TabsTrigger>
            <TabsTrigger value="tables">{t('tables')}</TabsTrigger>
            <TabsTrigger value="er">{t('er')}</TabsTrigger>
            <TabsTrigger value="sql">{t('sql')}</TabsTrigger>
            <TabsTrigger value="history">{t('history')}</TabsTrigger>
          </TabsList>
          <TabsContent value="query" className="space-y-4">
            <QueryWorkspace connected={connected} selection={selection}
              initialRequest={reuse?.request} initialSql={reuse?.sql} />
          </TabsContent>
          <TabsContent value="tables">
            <TablesBrowser tables={tables} dialect={dialect} onSchemaChanged={syncStatus}
              onReportFromTable={onReportFromTable} />
          </TabsContent>
          <TabsContent value="er">
            <ErDiagram connected={connected} />
          </TabsContent>
          <TabsContent value="sql">
            <SqlEditor connected={connected} />
          </TabsContent>
          <TabsContent value="history">
            <HistoryPanel onReuse={onReuse} />
          </TabsContent>
        </Tabs>
      ) : (
        <ReportsStudio selection={selection} tableToAnalyze={reportTable} tables={tables} />
      )}
    />
  );
}
