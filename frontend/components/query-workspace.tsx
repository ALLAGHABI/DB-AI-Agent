'use client';
import { AlertTriangle, Cloud, Cpu, Play, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { toast } from 'sonner';
import { api, type ExecResult, type GenerateResult } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import type { ModelSelection } from './providers-panel';
import { ResultsTable } from './results-table';

type Phase = 'idle' | 'generating' | 'running';

export function QueryWorkspace({ connected, selection }: {
  connected: boolean; selection: ModelSelection | null;
}) {
  const t = useTranslations('query');
  const ts = useTranslations('status');
  const [request, setRequest] = useState('');
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
        setResult(await api.execute(gen.sql));
      } else {
        setPendingWrite(gen);
      }
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setPhase('idle');
    }
  };

  const confirmWrite = async () => {
    if (!pendingWrite) return;
    setPendingWrite(null);
    setPhase('running');
    try {
      const res = await api.execute(pendingWrite.sql, true);
      setResult(res);
      toast.success(`${res.affected} ${t('affected')}`);
    } catch (e) {
      toast.error((e as Error).message);
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
          <Textarea rows={3} value={request} placeholder={t('placeholder')}
            onChange={e => setRequest(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) run(); }} />
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
              <TabsTrigger value="sql">{t('sql')}</TabsTrigger>
            </TabsList>
            <TabsContent value="data" className="pt-3">
              {result?.kind === 'rows'
                ? <ResultsTable columns={result.columns} rows={result.rows} />
                : result?.kind === 'affected'
                  ? <div className="py-8 text-center text-sm">{result.affected} {t('affected')}</div>
                  : <div className="py-12 text-center text-sm text-muted-foreground">{t('emptyHint')}</div>}
            </TabsContent>
            <TabsContent value="sql" className="pt-3">
              <pre dir="ltr" className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-sm leading-relaxed">
                {result?.applied_sql ?? generated?.sql ?? '-- …'}
              </pre>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Dialog open={!!pendingWrite} onOpenChange={open => !open && setPendingWrite(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />{t('confirmTitle')}
            </DialogTitle>
            <DialogDescription>{t('confirmBody')}</DialogDescription>
          </DialogHeader>
          <pre dir="ltr" className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-sm">
            {pendingWrite?.sql}
          </pre>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setPendingWrite(null)}>{t('cancel')}</Button>
            <Button variant="destructive" onClick={confirmWrite}>{t('confirmRun')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
