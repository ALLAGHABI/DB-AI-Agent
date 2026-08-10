'use client';
import { sql } from '@codemirror/lang-sql';
import CodeMirror from '@uiw/react-codemirror';
import { Play } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useTheme } from 'next-themes';
import { useState } from 'react';
import { toast } from 'sonner';
import { useApiError } from '@/lib/use-api-error';
import { api, type ExecResult } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ConfirmWriteDialog } from './confirm-write-dialog';
import { ResultsChart } from './results-chart';
import { ResultsTable } from './results-table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function SqlEditor({ connected }: { connected: boolean }) {
  const t = useTranslations('sqlEditor');
  const tq = useTranslations('query');
  const tc = useTranslations('chart');
  const { theme } = useTheme();
  const { showError } = useApiError();
  const [code, setCode] = useState('SELECT * FROM ');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExecResult | null>(null);
  const [pendingSql, setPendingSql] = useState<string | null>(null);

  const run = async (confirm = false) => {
    if (!code.trim()) return;
    setBusy(true);
    try {
      const res = await api.execute(code.trim(), confirm, { source: 'editor' });
      setResult(res);
      if (res.kind === 'affected') toast.success(tq('affectedCount', { count: res.affected }));
    } catch (e) {
      const err = e as { status?: number };
      if (err.status === 409) setPendingSql(code.trim());
      else showError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-0">
          <p className="text-xs text-muted-foreground">{t('hint')}</p>
        </CardHeader>
        <CardContent className="space-y-3 pt-3">
          <div dir="ltr" className="overflow-hidden rounded-lg border font-mono">
            <CodeMirror value={code} height="180px"
              theme={theme === 'dark' ? 'dark' : 'light'}
              extensions={[sql()]}
              placeholder={t('placeholder')}
              onChange={setCode} />
          </div>
          <div className="flex items-center justify-between gap-3">
            {!connected && <span className="text-xs text-destructive">{t('needsConnection')}</span>}
            <Button onClick={() => run(false)} disabled={!connected || busy || !code.trim()} className="gap-2">
              <Play className="h-4 w-4" />{busy ? t('running') : t('run')}
            </Button>
          </div>
          {result?.kind === 'rows' && (
            <Tabs defaultValue="data">
              <TabsList>
                <TabsTrigger value="data">{tq('results')}</TabsTrigger>
                <TabsTrigger value="chart">{tc('title')}</TabsTrigger>
              </TabsList>
              <TabsContent value="data" className="pt-3">
                <ResultsTable columns={result.columns} rows={result.rows} />
              </TabsContent>
              <TabsContent value="chart" className="pt-3">
                <ResultsChart columns={result.columns} rows={result.rows} />
              </TabsContent>
            </Tabs>
          )}
          {result?.kind === 'affected' && (
            <div className="py-4 text-center text-sm">{tq('affectedCount', { count: result.affected })}</div>
          )}
        </CardContent>
      </Card>
      <ConfirmWriteDialog sql={pendingSql}
        onConfirm={() => { setPendingSql(null); run(true); }}
        onCancel={() => setPendingSql(null)} />
    </>
  );
}
