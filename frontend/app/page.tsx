'use client';
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ConnectionsPanel } from '@/components/connections-panel';
import { ErDiagram } from '@/components/er-diagram';
import { ProvidersPanel, type ModelSelection } from '@/components/providers-panel';
import { QueryWorkspace } from '@/components/query-workspace';
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

  // استعادة حالة الاتصال بعد إعادة تحميل الصفحة (تبديل اللغة مثلاً)
  useEffect(() => {
    api.status().then(s => {
      if (s.db_connected) { setTables(s.tables); setDialect(s.dialect); }
    }).catch(() => {});
  }, []);

  const onConnected = useCallback((tbs: string[]) => {
    setTables(tbs);
    api.status().then(s => setDialect(s.dialect)).catch(() => {});
  }, []);

  const connected = tables.length > 0;

  return (
    <Shell connected={connected}
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
          </TabsList>
          <TabsContent value="query" className="space-y-4">
            <QueryWorkspace connected={connected} selection={selection} />
          </TabsContent>
          <TabsContent value="tables">
            <TablesBrowser tables={tables} dialect={dialect} />
          </TabsContent>
          <TabsContent value="er">
            <ErDiagram connected={connected} />
          </TabsContent>
          <TabsContent value="sql">
            <SqlEditor connected={connected} />
          </TabsContent>
        </Tabs>
      }
    />
  );
}
