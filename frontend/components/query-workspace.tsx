'use client';
import { Cloud, Cpu, Database, Play, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useApiError } from '@/lib/use-api-error';
import { api, type ExecResult, type GenerateResult } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { ConfirmWriteDialog } from './confirm-write-dialog';
import type { ModelSelection } from './providers-panel';
import { ResultsChart } from './results-chart';
import { ResultsTable } from './results-table';

type Phase = 'idle' | 'generating' | 'running';

export function QueryWorkspace({ connected, selection, initialRequest, initialSql }: {
  connected: boolean; selection: ModelSelection | null;
  initialRequest?: string; initialSql?: string;
}) {
  const t = useTranslations('query');
  const ts = useTranslations('status');
  const tc = useTranslations('chart');
  const { showError } = useApiError();
  const [request, setRequest] = useState('');

  // إعادة استخدام استعلام من السجل
  useEffect(() => {
    if (initialRequest !== undefined) setRequest(initialRequest);
  }, [initialRequest]);
  useEffect(() => {
    if (!initialSql) return;
    setGenerated({ sql: initialSql, sql_class: 'read', provider: '', model: '', is_local: true });
    api.execute(initialSql, false, { source: 'editor' })
      .then(setResult).catch(showError);
  }, [initialSql]);   // eslint-disable-line react-hooks/exhaustive-deps
  const [phase, setPhase] = useState<Phase>('idle');
  const [generated, setGenerated] = useState<GenerateResult | null>(null);
  const [result, setResult] = useState<ExecResult | null>(null);
  const [pendingWrite, setPendingWrite] = useState<GenerateResult | null>(null);
  const ready = connected && !!selection;

  const run = async () => {
    if (!request.trim() || !selection) return;
    setPhase('generating');
    setResult(null);
    setGenerated(null);
    try {
      const gen = await api.generate(request.trim(), selection.provider, selection.model);
      setGenerated(gen);
      if (gen.sql_class === 'read') {
        setPhase('running');
        setResult(await api.execute(gen.sql, false,
          { source: 'nl', request: request.trim(), model: selection.model }));
      } else {
        setPendingWrite(gen);
      }
    } catch (e) {
      showError(e);
    } finally {
      setPhase('idle');
    }
  };

  const confirmWrite = async () => {
    if (!pendingWrite) return;
    setPendingWrite(null);
    setPhase('running');
    try {
      const res = await api.execute(pendingWrite.sql, true,
        { source: 'nl', request: request.trim(), model: selection?.model });
      setResult(res);
      toast.success(t('affectedCount', { count: res.affected }));
    } catch (e) {
      showError(e);
    } finally {
      setPhase('idle');
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">{t('title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!ready && (
            <ol className="space-y-1.5 rounded-lg border border-dashed p-3 text-xs">
              <li className={connected ? 'text-muted-foreground line-through' : 'font-medium'}>
                <span className="me-1.5">①</span>{t('step1')}
              </li>
              <li className={selection ? 'text-muted-foreground line-through' : 'font-medium'}>
                <span className="me-1.5">②</span>{t('step2')}
              </li>
            </ol>
          )}
          <Textarea rows={3} value={request} dir="auto" placeholder={t('placeholder')}
            onChange={e => setRequest(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) run(); }} />
          <div className="flex flex-wrap gap-1.5">
            {['example1', 'example2', 'example3'].map(k => t(k)).map(ex => (
              <button key={ex} type="button" onClick={() => setRequest(ex)}
                className="cursor-pointer rounded-full border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary hover:bg-accent hover:text-foreground">
                {ex}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between">
            {selection ? (
              <Badge variant="outline" className="gap-1.5 font-mono text-xs">
                {selection.isLocal
                  ? <Cpu className="h-3 w-3 text-primary" />
                  : <Cloud className="h-3 w-3 text-sky-500" />}
                {selection.model}
                <span className="text-muted-foreground">· {selection.isLocal ? ts('local') : ts('cloud')}</span>
              </Badge>
            ) : <span className="text-xs text-muted-foreground">{t('needsSetup')}</span>}
            <Button onClick={run} disabled={!ready || phase !== 'idle' || !request.trim()} className="gap-2">
              {phase === 'generating' ? <Sparkles className="h-4 w-4 animate-pulse" /> : <Play className="h-4 w-4" />}
              {phase === 'generating' ? t('generating') : phase === 'running' ? t('running') : t('run')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <Tabs defaultValue="data">
            <TabsList>
              <TabsTrigger value="data">{t('results')}</TabsTrigger>
              <TabsTrigger value="chart" disabled={result?.kind !== 'rows'}>{tc('title')}</TabsTrigger>
              <TabsTrigger value="sql">{t('sql')}</TabsTrigger>
            </TabsList>
            <TabsContent value="data" className="pt-3">
              {result?.kind === 'rows'
                ? <ResultsTable columns={result.columns} rows={result.rows} />
                : result?.kind === 'affected'
                  ? <div className="py-8 text-center text-sm">{t('affectedCount', { count: result.affected })}</div>
                  : (
                    <div className="flex flex-col items-center gap-3 py-14 text-center">
                      <Database className="h-10 w-10 text-primary/30" aria-hidden />
                      <p className="text-sm text-muted-foreground">{t('emptyHint')}</p>
                    </div>
                  )}
            </TabsContent>
            <TabsContent value="chart" className="pt-3">
              {result?.kind === 'rows'
                ? <ResultsChart columns={result.columns} rows={result.rows} />
                : <p className="py-10 text-center text-sm text-muted-foreground">{t('emptyHint')}</p>}
            </TabsContent>
            <TabsContent value="sql" className="pt-3">
              <pre dir="ltr" className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-sm leading-relaxed">
                {result?.applied_sql ?? generated?.sql ?? '-- …'}
              </pre>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <ConfirmWriteDialog sql={pendingWrite?.sql ?? null}
        onConfirm={confirmWrite}
        onCancel={() => setPendingWrite(null)} />
    </>
  );
}
