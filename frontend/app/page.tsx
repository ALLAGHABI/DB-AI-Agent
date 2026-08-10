'use client';
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ConnectionsPanel } from '@/components/connections-panel';
import { ErDiagram } from '@/components/er-diagram';
import { ProvidersPanel, type ModelSelection } from '@/components/providers-panel';
import { QueryWorkspace } from '@/components/query-workspace';
import { ReportsStudio } from '@/components/reports-studio';
import { Shell } from '@/components/shell';
import { SqlEditor } from '@/components/sql-editor';
import { TablesBrowser } from '@/components/tables-browser';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';

export default function Home() {
  const t = useTranslations('nav');
  const [tables, setTables] = useState<string[]>([]);
  const [dialect, setDialect] = useState<string | null>(null);
  const [selection, setSelection] = useState<ModelSelection | null>(null);
  const onModelChange = useCallback((s: ModelSelection | null) => setSelection(s), []);

  const [apiDown, setApiDown] = useState(false);

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

  // استعادة حالة الاتصال بعد إعادة تحميل الصفحة (تبديل اللغة مثلاً)
  useEffect(() => { syncStatus(); }, [syncStatus]);

  const onConnected = useCallback((tbs: string[]) => {
    setTables(tbs);
    syncStatus();
  }, [syncStatus]);

  const connected = tables.length > 0;

  return (
    <Shell connected={connected} apiDown={apiDown}
      sidebar={<>
        <ConnectionsPanel onConnected={onConnected} />
        <ProvidersPanel onModelChange={onModelChange} />
      </>}
      main={
        <Tabs defaultValue="query">
          <TabsList className="mb-2">
            <TabsTrigger value="query">{t('query')}</TabsTrigger>
            <TabsTrigger value="tables">{t('tables')}</TabsTrigger>
            <TabsTrigger value="er">{t('er')}</TabsTrigger>
            <TabsTrigger value="sql">{t('sql')}</TabsTrigger>
            <TabsTrigger value="reports">{t('reports')}</TabsTrigger>
          </TabsList>
          <TabsContent value="query" className="space-y-4">
            <QueryWorkspace connected={connected} selection={selection} />
          </TabsContent>
          <TabsContent value="tables">
            <TablesBrowser tables={tables} dialect={dialect} onSchemaChanged={syncStatus} />
          </TabsContent>
          <TabsContent value="er">
            <ErDiagram connected={connected} />
          </TabsContent>
          <TabsContent value="sql">
            <SqlEditor connected={connected} />
          </TabsContent>
          <TabsContent value="reports">
            <ReportsStudio selection={selection} />
          </TabsContent>
        </Tabs>
      }
    />
  );
}
