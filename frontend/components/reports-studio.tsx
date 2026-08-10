'use client';
import {
  Cloud, Cpu, Database, Download, ExternalLink, FileBarChart, FileSpreadsheet,
  FileText, Sparkles, Trash2, Upload,
} from 'lucide-react';
import { useFormatter, useLocale, useTranslations } from 'next-intl';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { useApiError } from '@/lib/use-api-error';
import {
  ApiError, api, type ReportMeta, type ReportProfile,
  type SemanticOverride, type Semantics,
} from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { ModelSelection } from './providers-panel';

export function ReportsStudio({ selection, tableToAnalyze, tables = [] }: {
  selection: ModelSelection | null; tableToAnalyze?: string; tables?: string[];
}) {
  const t = useTranslations('reports');
  const locale = useLocale();
  const format = useFormatter();
  const { showError } = useApiError();
  // النماذج الصغيرة (≤2B) تتجاهل اللغة وتختلق الأرقام — ننبّه قبل التوليد
  const isSmallModel = /(^|[^\d])(0\.\d|1|1\.\d|2)b\b/i.test(selection?.model ?? '');
  const fileRef = useRef<HTMLInputElement>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<ReportProfile | null>(null);
  const [sourceName, setSourceName] = useState('');
  const [title, setTitle] = useState('');
  const [template, setTemplate] = useState('executive');
  const [language, setLanguage] = useState(locale);
  const [generating, setGenerating] = useState(false);
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [tab, setTab] = useState('new');
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [semantics, setSemantics] = useState<Record<string, Semantics>>({});
  const [overrides, setOverrides] = useState<Record<string, SemanticOverride>>({});
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [sheets, setSheets] = useState<string[]>([]);

  // الأعمدة التي ستظهر فعلاً في التقرير — هي وحدها تستحق إعادة تسمية
  const usedColumns = Object.entries(semantics).flatMap(([table, sem]) => {
    const ov = overrides[table] ?? {};
    const measure = ov.measure ?? sem.measures[0];
    const date = ov.date ?? sem.dates[0];
    const dims = ov.dimensions ?? sem.dimensions.slice(0, 3);
    return [measure, date, ...dims].filter(Boolean) as string[];
  }).filter((c, i, arr) => arr.indexOf(c) === i);

  const analyzeTables = async (names: string[]) => {
    if (!names.length) return;
    setAnalyzing(true);
    setProfile(null); setToken(null);
    try {
      const res = await api.reportAnalyzeTables(names, language);
      setToken(res.token);
      setProfile(res.profile);
      setSemantics(res.semantics ?? {});
      setLabels(res.labels ?? {});
      setSheets([]);
      setOverrides({});
      const label = names.length === 1 ? names[0] : t('allTables');
      setSourceName(label);
      setTitle(label);
    } catch (e) { showError(e); } finally { setAnalyzing(false); }
  };

  useEffect(() => { api.reportsList().then(setReports).catch(showError); }, [showError]);

  // تحليل جدول متصل مباشرة (زر "تقرير من هذا الجدول")
  useEffect(() => {
    if (!tableToAnalyze) return;
    setTab('new');
    setPicked(new Set([tableToAnalyze]));
    analyzeTables([tableToAnalyze]);
  }, [tableToAnalyze]);   // eslint-disable-line react-hooks/exhaustive-deps

  const analyze = async (file: File) => {
    setAnalyzing(true);
    setProfile(null); setToken(null);
    try {
      const res = await api.reportAnalyze(file, language);
      setToken(res.token);
      setProfile(res.profile);
      setSemantics(res.semantics ?? {});
      setLabels(res.labels ?? {});
      setSheets(res.sheets ?? []);
      setOverrides({});
      setSourceName(file.name);
      if (!title) setTitle(file.name.replace(/\.[^.]+$/, ''));
    } catch (e) {
      showError(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const generate = async () => {
    if (!token || !selection) return;
    setGenerating(true);
    try {
      const { job_id } = await api.reportGenerate({
        token, title: title || sourceName, template, language,
        provider: selection.provider, model: selection.model,
        overrides: Object.keys(overrides).length ? overrides : undefined,
        labels: Object.keys(labels).length ? labels : undefined,
      });
      // التوليد المحلي قد يستغرق دقيقة — نستطلع الحالة بدل انتظار طلب طويل يُقطع
      for (;;) {
        await new Promise(r => setTimeout(r, 1500));
        const job = await api.reportJob(job_id);
        if (job.status === 'running') continue;
        if (job.status === 'failed') {
          showError(new ApiError(job.error.code, job.error.params ?? {}));
          return;
        }
        setReports(r => [job.report, ...r]);
        toast.success(t('generated'));
        if (job.report.dropped_claims) {
          toast.warning(t('droppedWarn', { count: job.report.dropped_claims }));
        }
        if (job.report.language_ok === false) toast.warning(t('languageWarn'));
        else if (job.report.used_fallback) toast.info(t('fallbackNote'));
        setTab('archive');
        return;
      }
    } catch (e) {
      showError(e);
    } finally {
      setGenerating(false);
    }
  };

  const remove = async () => {
    if (!deleteId) return;
    try {
      await api.reportDelete(deleteId);
      setReports(r => r.filter(x => x.id !== deleteId));
      toast.success(t('deleted'));
      setDeleteId(null);
    } catch (e) { showError(e); }
  };

  return (
    <Tabs value={tab} onValueChange={v => v && setTab(v)} className="space-y-4">
      <TabsList>
        <TabsTrigger value="new">{t('newTab')}</TabsTrigger>
        <TabsTrigger value="archive">{t('archiveTab')}</TabsTrigger>
      </TabsList>

      <TabsContent value="new">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">{t('title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <button type="button"
            className={`flex w-full cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed p-8 text-sm text-muted-foreground transition-colors hover:border-primary hover:bg-accent/40 ${dragging ? 'border-primary bg-accent/40' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => {
              e.preventDefault(); setDragging(false);
              const f = e.dataTransfer.files?.[0];
              if (f) analyze(f);
            }}
            onClick={() => fileRef.current?.click()}>
            <Upload className="h-6 w-6" />
            {analyzing ? t('analyzing') : t('uploadHint')}
            <span className="text-xs">{sourceName || t('pickFile')}</span>
          </button>
          <input ref={fileRef} type="file" hidden accept=".csv,.xlsx,.xls,.json"
            onChange={e => e.target.files?.[0] && analyze(e.target.files[0])} />
          {!selection && <p className="text-xs text-destructive">{t('needModel')}</p>}

          {tables.length > 0 && (
            <div className="space-y-3 rounded-xl border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Database className="h-4 w-4 text-primary" aria-hidden />
                  {t('fromTable')}
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" className="h-7 text-xs"
                    onClick={() => setPicked(new Set(tables))}>{t('selectAll')}</Button>
                  <Button variant="ghost" size="sm" className="h-7 text-xs"
                    disabled={!picked.size}
                    onClick={() => setPicked(new Set())}>{t('clearSel')}</Button>
                </div>
              </div>

              <p className="text-xs text-muted-foreground">{t('pickTables')}</p>
              <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
                {tables.map(tb => {
                  const on = picked.has(tb);
                  return (
                    <button key={tb} type="button" aria-pressed={on}
                      onClick={() => setPicked(s => {
                        const next = new Set(s);
                        if (next.has(tb)) next.delete(tb); else next.add(tb);
                        return next;
                      })}
                      className={`cursor-pointer rounded-full border px-3 py-1 font-mono text-xs transition-colors
                        ${on
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:border-primary hover:text-foreground'}`}>
                      {tb}
                    </button>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <Button size="sm" className="gap-1.5" disabled={!picked.size || analyzing}
                  onClick={() => analyzeTables([...picked])}>
                  <FileBarChart className="h-3.5 w-3.5" />
                  {t('analyzeSelected', { count: picked.size })}
                </Button>
                <Button variant="outline" size="sm" disabled={analyzing}
                  onClick={() => { setPicked(new Set(tables)); analyzeTables(tables); }}>
                  {t('analyzeAll')}
                </Button>
              </div>
            </div>
          )}

          {profile && (
            <>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {(profile.kind === 'multi' ? [
                  [format.number(profile.overview.tables), t('tablesCount')],
                  [format.number(profile.overview.rows), t('totalRows')],
                  [format.number(profile.overview.cols), t('cols')],
                  [format.number(profile.overview.relationships), t('relationships')],
                ] : [
                  [format.number(profile.overview.rows), t('rows')],
                  [format.number(profile.overview.cols), t('cols')],
                  [format.number(profile.overview.missing_pct / 100, { style: 'percent', maximumFractionDigits: 2 }), t('missing')],
                  [format.number(profile.overview.duplicate_rows), t('duplicates')],
                ]).map(([v, l]) => (
                  <div key={l} className="rounded-lg border bg-muted/40 p-3 text-center">
                    <div className="text-xl font-bold tabular-nums">{v}</div>
                    <div className="text-xs text-muted-foreground">{l}</div>
                  </div>
                ))}
              </div>
              {sheets.length > 1 && (
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">
                    {t('sheetsFound', { count: sheets.length })}
                  </Label>
                  <div className="flex flex-wrap gap-1.5">
                    {sheets.map(s => (
                      <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                {profile.kind === 'multi' && (
                  <Label className="text-xs text-muted-foreground">{t('perTable')}</Label>
                )}
                <div className="flex flex-wrap gap-1.5">
                  {profile.kind === 'multi'
                    ? profile.datasets.map(d => (
                      <Badge key={d.name} variant="outline" className="font-mono text-xs">
                        {d.name}
                        <span className="text-muted-foreground">
                          {' · '}{format.number(d.profile.overview.rows)}
                        </span>
                      </Badge>
                    ))
                    : profile.columns.map(c => (
                      <Badge key={c.name} variant="outline" className="font-mono text-xs">
                        {c.name} <span className="text-muted-foreground">· {c.kind}</span>
                      </Badge>
                    ))}
                </div>
              </div>

              {Object.keys(semantics).length > 0 && (
                <div className="space-y-2 rounded-xl border p-3">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Sparkles className="h-4 w-4 text-primary" aria-hidden />
                    {t('analysisBasis')}
                  </div>
                  <p className="text-xs text-muted-foreground">{t('autoDetected')}</p>
                  {Object.entries(semantics).map(([table, sem]) => {
                    const ov = overrides[table] ?? {};
                    const measure = ov.measure ?? sem.measures[0] ?? '';
                    const date = ov.date ?? sem.dates[0] ?? '';
                    const setOv = (patch: SemanticOverride) =>
                      setOverrides(o => ({ ...o, [table]: { ...o[table], ...patch } }));
                    return (
                      <div key={table} className="flex flex-wrap items-end gap-2">
                        {Object.keys(semantics).length > 1 && (
                          <Badge variant="outline" className="font-mono text-xs">{table}</Badge>
                        )}
                        <div className="space-y-1">
                          <Label className="text-xs text-muted-foreground">{t('measureCol')}</Label>
                          <Select value={measure || '—'}
                            onValueChange={v => v && setOv({ measure: v === '—' ? null : v })}>
                            <SelectTrigger className="w-40 font-mono text-xs"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="—" className="text-xs">{t('none')}</SelectItem>
                              {sem.measures.map(m => (
                                <SelectItem key={m} value={m} className="font-mono text-xs">{m}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        {sem.dates.length > 0 && (
                          <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">{t('dateCol')}</Label>
                            <Select value={date || '—'}
                              onValueChange={v => v && setOv({ date: v === '—' ? null : v })}>
                              <SelectTrigger className="w-40 font-mono text-xs"><SelectValue /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="—" className="text-xs">{t('none')}</SelectItem>
                                {sem.dates.map(d => (
                                  <SelectItem key={d} value={d} className="font-mono text-xs">{d}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        )}
                        {sem.dimensions.length > 0 && (
                          <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">{t('dimCols')}</Label>
                            <div className="flex flex-wrap gap-1">
                              {sem.dimensions.slice(0, 6).map(d => {
                                const chosen = ov.dimensions ?? sem.dimensions.slice(0, 3);
                                const on = chosen.includes(d);
                                return (
                                  <button key={d} type="button" aria-pressed={on}
                                    onClick={() => setOv({ dimensions: on
                                      ? chosen.filter(x => x !== d) : [...chosen, d] })}
                                    className={`cursor-pointer rounded-full border px-2.5 py-0.5 font-mono text-xs transition-colors
                                      ${on ? 'border-primary bg-primary text-primary-foreground'
                                           : 'text-muted-foreground hover:border-primary'}`}>
                                    {d}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {usedColumns.length > 0 && (
                    <div className="space-y-1.5 border-t pt-2">
                      <Label className="text-xs text-muted-foreground">{t('labelsTitle')}</Label>
                      <p className="text-xs text-muted-foreground">{t('labelsHint')}</p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {usedColumns.map(col => (
                          <div key={col} className="flex items-center gap-2">
                            <span className="w-28 shrink-0 truncate font-mono text-xs text-muted-foreground"
                              dir="ltr" title={col}>{col}</span>
                            <Input dir="auto" className="h-8 text-sm"
                              value={labels[col] ?? ''}
                              onChange={e => setLabels(l => ({ ...l, [col]: e.target.value }))} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5 sm:col-span-3">
                  <Label className="text-xs">{t('reportTitle')}</Label>
                  <Input dir="auto" value={title} onChange={e => setTitle(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('template')}</Label>
                  <Select value={template} onValueChange={v => v && setTemplate(v)}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="executive">{t('tExecutive')}</SelectItem>
                      <SelectItem value="detailed">{t('tDetailed')}</SelectItem>
                      <SelectItem value="dashboard">{t('tDashboard')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('language')}</Label>
                  <Select value={language} onValueChange={v => v && setLanguage(v)}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ar">{t('arabic')}</SelectItem>
                      <SelectItem value="en">{t('english')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end">
                  <Button className="w-full gap-2" onClick={generate}
                    disabled={!selection || generating}>
                    <Sparkles className={`h-4 w-4 ${generating ? 'animate-pulse' : ''}`} />
                    {generating ? t('generating') : t('generate')}
                  </Button>
                </div>
              </div>
              {!selection && <p className="text-xs text-destructive">{t('needModel')}</p>}

          {tables.length > 0 && (
            <div className="space-y-3 rounded-xl border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Database className="h-4 w-4 text-primary" aria-hidden />
                  {t('fromTable')}
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" className="h-7 text-xs"
                    onClick={() => setPicked(new Set(tables))}>{t('selectAll')}</Button>
                  <Button variant="ghost" size="sm" className="h-7 text-xs"
                    disabled={!picked.size}
                    onClick={() => setPicked(new Set())}>{t('clearSel')}</Button>
                </div>
              </div>

              <p className="text-xs text-muted-foreground">{t('pickTables')}</p>
              <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
                {tables.map(tb => {
                  const on = picked.has(tb);
                  return (
                    <button key={tb} type="button" aria-pressed={on}
                      onClick={() => setPicked(s => {
                        const next = new Set(s);
                        if (next.has(tb)) next.delete(tb); else next.add(tb);
                        return next;
                      })}
                      className={`cursor-pointer rounded-full border px-3 py-1 font-mono text-xs transition-colors
                        ${on
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:border-primary hover:text-foreground'}`}>
                      {tb}
                    </button>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2 pt-1">
                <Button size="sm" className="gap-1.5" disabled={!picked.size || analyzing}
                  onClick={() => analyzeTables([...picked])}>
                  <FileBarChart className="h-3.5 w-3.5" />
                  {t('analyzeSelected', { count: picked.size })}
                </Button>
                <Button variant="outline" size="sm" disabled={analyzing}
                  onClick={() => { setPicked(new Set(tables)); analyzeTables(tables); }}>
                  {t('analyzeAll')}
                </Button>
              </div>
            </div>
          )}
            </>
          )}
        </CardContent>
      </Card>

      </TabsContent>

      <TabsContent value="archive">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">{t('archive')}</CardTitle>
        </CardHeader>
        <CardContent>
          {!reports.length ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{t('empty')}</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {reports.map(r => (
                <div key={r.id} className="space-y-2 rounded-xl border p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 font-semibold">
                        <FileText className="h-4 w-4 text-primary" />{r.title}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        <bdi>{r.source_name}</bdi> · {format.number(r.rows)} × {format.number(r.cols)}
                        {' · '}
                        {r.created_iso
                          ? format.dateTime(new Date(r.created_iso), { dateStyle: 'medium', timeStyle: 'short' })
                          : r.created_at}
                      </div>
                    </div>
                    <Badge variant="outline" className="gap-1 text-xs">
                      {r.is_local ? <Cpu className="h-3 w-3 text-primary" /> : <Cloud className="h-3 w-3" />}
                      {r.is_local ? t('localBadge') : t('cloudBadge')}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <Button variant="outline" size="sm" className="gap-1.5"
                      onClick={() => window.open(api.reportFileUrl(r.id, 'html'), '_blank')}>
                      <ExternalLink className="h-3.5 w-3.5" />{t('view')}
                    </Button>
                    {r.pdf && (
                      <Button variant="outline" size="sm" className="gap-1.5"
                        onClick={() => { window.location.href = api.reportFileUrl(r.id, 'pdf'); }}>
                        <Download className="h-3.5 w-3.5" />PDF
                      </Button>
                    )}
                    <Button variant="outline" size="sm" className="gap-1.5"
                      onClick={() => { window.location.href = api.reportFileUrl(r.id, 'xlsx'); }}>
                      <FileSpreadsheet className="h-3.5 w-3.5" />Excel
                    </Button>
                    <Button variant="ghost" size="sm" className="gap-1.5 text-destructive"
                      onClick={() => setDeleteId(r.id)}>
                      <Trash2 className="h-3.5 w-3.5" />{t('delete')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      </TabsContent>

      <Dialog open={!!deleteId} onOpenChange={o => !o && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('deleteConfirm')}</DialogTitle></DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDeleteId(null)}>{t('cancel')}</Button>
            <Button variant="destructive" onClick={remove}>{t('delete')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Tabs>
  );
}
