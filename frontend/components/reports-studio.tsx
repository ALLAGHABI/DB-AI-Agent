'use client';
import {
  BarChart3, BarChartHorizontal, ChartLine, Cloud, Cpu, Database, Download,
  ExternalLink, Eye, EyeOff, FileBarChart, FileSpreadsheet, FileText, PieChart,
  Plus, Sparkles, Trash2, Upload,
} from 'lucide-react';
import { useFormatter, useLocale, useTranslations } from 'next-intl';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { useApiError } from '@/lib/use-api-error';
import {
  ApiError, api, type ChartType, type ReportMeta, type ReportProfile,
  type ReportSection, type SemanticOverride, type Semantics,
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

/** الأقسام التي يبدأ بها كل قالب — والمستخدم يعدّلها بعد ذلك بحرية. */
const TEMPLATE_SECTIONS: Record<string, ReportSection[]> = {
  executive: ['summary', 'findings', 'charts', 'recommendations'],
  dashboard: ['summary', 'findings', 'charts'],
  detailed: ['summary', 'findings', 'charts', 'recommendations', 'appendix'],
};
const SECTION_ORDER: ReportSection[] =
  ['summary', 'findings', 'charts', 'recommendations', 'appendix'];
const SECTION_KEY: Record<ReportSection, string> = {
  summary: 'secSummary', findings: 'secFindings', charts: 'secCharts',
  recommendations: 'secRecommendations', appendix: 'secAppendix',
};

/** سقف الرسوم الافتراضية لكل قالب — والباقي يضيفه المستخدم بنفسه. */
const CHART_CAP: Record<string, number> = { executive: 3, dashboard: 6, detailed: 10 };

const CHART_TYPES: Record<'trend' | 'breakdown', ChartType[]> = {
  trend: ['line', 'column'],
  breakdown: ['bar', 'column', 'donut'],
};
const TYPE_ICON = {
  bar: BarChartHorizontal, column: BarChart3, line: ChartLine, donut: PieChart,
} as const;

type ChartItem = {
  key: string; table: string; kind: 'trend' | 'breakdown';
  column?: string; type: ChartType; on: boolean;
};

function defaultCharts(semantics: Record<string, Semantics>,
                       overrides: Record<string, SemanticOverride>,
                       cap: number): ChartItem[] {
  const all = Object.entries(semantics).flatMap(([table, sem]) => {
    const ov = overrides[table] ?? {};
    const date = ov.date === null ? undefined : ov.date ?? sem.dates[0];
    const dims = ov.dimensions ?? sem.dimensions.slice(0, 3);
    const items: ChartItem[] = [];
    if (date) {
      items.push({ key: `${table}::trend`, table, kind: 'trend', type: 'line', on: true });
    }
    for (const d of dims) {
      items.push({ key: `${table}::${d}`, table, kind: 'breakdown', column: d,
        type: 'bar', on: true });
    }
    return items;
  });
  // نُقدّم اتجاهات كل جدول على توزيعاته حتى لا يبتلع جدولٌ واحد كل الخانات
  const trends = all.filter(c => c.kind === 'trend');
  const rest = all.filter(c => c.kind !== 'trend');
  return [...trends, ...rest].slice(0, cap);
}

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
  const [sourceOpen, setSourceOpen] = useState(true);
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
  const [sections, setSections] = useState<ReportSection[]>(TEMPLATE_SECTIONS.executive);
  // نخزّن تعديلات المستخدم فقط؛ قائمة الرسوم نفسها مشتقة من أساس التحليل الحالي
  const [chartPrefs, setChartPrefs] =
    useState<Record<string, { type?: ChartType; on?: boolean }>>({});
  const [extraDims, setExtraDims] = useState<{ table: string; column: string }[]>([]);

  const lbl = (col?: string) => (col ? labels[col] || col : '');

  // الأعمدة التي ستظهر فعلاً في التقرير — هي وحدها تستحق إعادة تسمية
  const usedColumns = Object.entries(semantics).flatMap(([table, sem]) => {
    const ov = overrides[table] ?? {};
    const measure = ov.measure ?? sem.measures[0];
    const date = ov.date ?? sem.dates[0];
    const dims = ov.dimensions ?? sem.dimensions.slice(0, 3);
    return [measure, date, ...dims].filter(Boolean) as string[];
  }).filter((c, i, arr) => arr.indexOf(c) === i);

  // تغيير أساس التحليل يعيد بناء القائمة تلقائياً، وتفضيلات المستخدم تبقى فوقها
  const base = defaultCharts(semantics, overrides, CHART_CAP[template] ?? 3);
  const charts: ChartItem[] = [
    ...base,
    ...extraDims
      .filter(e => !base.some(b => b.key === `${e.table}::${e.column}`))
      .map(e => ({
        key: `${e.table}::${e.column}`, table: e.table,
        kind: 'breakdown' as const, column: e.column,
        type: 'bar' as ChartType, on: true,
      })),
  ].map(c => ({ ...c, ...chartPrefs[c.key] }));

  const reset = () => {
    setProfile(null); setToken(null);
    setChartPrefs({}); setExtraDims([]);
    setSections(TEMPLATE_SECTIONS[template] ?? TEMPLATE_SECTIONS.executive);
  };

  const analyzeTables = async (names: string[]) => {
    if (!names.length) return;
    setAnalyzing(true);
    reset();
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
      setSourceOpen(false);
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
    reset();
    try {
      const res = await api.reportAnalyze(file, language);
      setToken(res.token);
      setProfile(res.profile);
      setSemantics(res.semantics ?? {});
      setLabels(res.labels ?? {});
      setSheets(res.sheets ?? []);
      setOverrides({});
      setSourceName(file.name);
      setTitle(file.name.replace(/\.(csv|xlsx?|json)(-\d+)?$/i, '').replace(/\s*\(\d+\)$/, ''));
      setSourceOpen(false);
    } catch (e) {
      showError(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const pickTemplate = (value: string) => {
    setTemplate(value);
    setSections(TEMPLATE_SECTIONS[value] ?? TEMPLATE_SECTIONS.executive);
  };

  const toggleSection = (key: ReportSection) =>
    setSections(s => (s.includes(key) ? s.filter(x => x !== key)
      : SECTION_ORDER.filter(x => x === key || s.includes(x))));

  const patchChart = (key: string, patch: { type?: ChartType; on?: boolean }) =>
    setChartPrefs(p => ({ ...p, [key]: { ...p[key], ...patch } }));

  // بُعد لم يُضَف بعد لأي رسم — «أضف رسماً» بلا خيارات لا معنى له
  const spareDim = Object.entries(semantics).flatMap(([table, sem]) =>
    sem.dimensions.map(d => ({ table, d })))
    .find(({ table, d }) => !charts.some(c => c.key === `${table}::${d}`));

  const addChart = () => {
    if (!spareDim) return;
    setExtraDims(e => [...e, { table: spareDim.table, column: spareDim.d }]);
  };

  const activeCharts = charts.filter(c => c.on);

  const generate = async () => {
    if (!token || !selection) return;
    setGenerating(true);
    try {
      const { job_id } = await api.reportGenerate({
        token, title: title || sourceName, template, language,
        provider: selection.provider, model: selection.model,
        overrides: Object.keys(overrides).length ? overrides : undefined,
        labels: Object.keys(labels).length ? labels : undefined,
        sections,
        charts: sections.includes('charts')
          ? activeCharts.map(({ table, kind, column, type }) =>
            ({ table, kind, column, type }))
          : [],
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

  const sourcePicker = (
    <div className="grid gap-3 sm:grid-cols-2">
      <button type="button"
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-sm text-muted-foreground transition-colors hover:border-primary hover:bg-accent/40 ${dragging ? 'border-primary bg-accent/40' : ''}`}
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
        <span className="text-xs">{t('pickFile')}</span>
      </button>
      <input ref={fileRef} type="file" hidden accept=".csv,.xlsx,.xls,.json"
        onChange={e => e.target.files?.[0] && analyze(e.target.files[0])} />

      {tables.length > 0 ? (
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
          <div className="flex max-h-32 flex-wrap gap-1.5 overflow-y-auto">
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
                    ${on ? 'border-primary bg-primary text-primary-foreground'
                         : 'text-muted-foreground hover:border-primary hover:text-foreground'}`}>
                  {tb}
                </button>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2">
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
      ) : <div />}
    </div>
  );

  return (
    <Tabs value={tab} onValueChange={v => v && setTab(v)} className="space-y-4">
      <TabsList>
        <TabsTrigger value="new">{t('newTab')}</TabsTrigger>
        <TabsTrigger value="archive">{t('archiveTab')}</TabsTrigger>
      </TabsList>

      <TabsContent value="new" className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex flex-wrap items-center justify-between gap-2 text-sm">
              {t('title')}
              {profile && !sourceOpen && (
                <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground">
                  <bdi>{t('sourceBar', {
                    source: sourceName,
                    rows: format.number(profile.overview.rows),
                    cols: format.number(profile.overview.cols),
                  })}</bdi>
                  {sheets.length > 1 && (
                    <Badge variant="secondary" className="text-[11px]">
                      {t('sheetsFound', { count: sheets.length })}
                    </Badge>
                  )}
                  <Button variant="ghost" size="sm" className="h-6 px-2 text-xs"
                    onClick={() => setSourceOpen(true)}>{t('changeSource')}</Button>
                </span>
              )}
            </CardTitle>
          </CardHeader>
          {(sourceOpen || !profile) && (
            <CardContent className="space-y-3">
              {sourcePicker}
              {!selection && <p className="text-xs text-destructive">{t('needModel')}</p>}
            </CardContent>
          )}
        </Card>

        {profile && (
          <div className="grid gap-4 lg:grid-cols-[1fr_18rem]">
            {/* ——— مخطط التقرير: ما تراه هو ما سيُولَّد ——— */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{t('outline')}</CardTitle>
                <p className="text-xs text-muted-foreground">{t('outlineHint')}</p>
              </CardHeader>
              <CardContent className="space-y-2">
                {SECTION_ORDER.map(key => {
                  const on = sections.includes(key);
                  return (
                    <div key={key} className="space-y-2">
                      <button type="button" aria-pressed={on}
                        onClick={() => toggleSection(key)}
                        className={`flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border px-3 py-2 text-start text-sm transition-colors
                          ${on ? 'border-primary/40 bg-accent/40 font-medium'
                               : 'text-muted-foreground hover:border-primary/40'}`}>
                        <span className="flex items-center gap-2">
                          <span className={`h-2 w-2 rounded-full ${on ? 'bg-primary' : 'bg-muted-foreground/40'}`} />
                          {t(SECTION_KEY[key])}
                        </span>
                        {on ? <Eye className="h-4 w-4 text-primary" />
                            : <EyeOff className="h-4 w-4" />}
                      </button>

                      {key === 'charts' && on && (
                        <div className="space-y-2 ps-4">
                          {charts.map(c => {
                            const heading = c.kind === 'trend'
                              ? t('chartTrend')
                              : t('chartBy', { dim: lbl(c.column) });
                            const Icon = TYPE_ICON[c.type];
                            return (
                              <div key={c.key}
                                className={`flex flex-wrap items-center gap-2 rounded-lg border p-2 ${c.on ? '' : 'opacity-55'}`}>
                                <Icon className="h-4 w-4 shrink-0 text-primary" aria-hidden />
                                <span className="min-w-0 flex-1 truncate text-xs">
                                  {Object.keys(semantics).length > 1 && (
                                    <span className="me-1 font-mono text-muted-foreground">
                                      {lbl(c.table)}
                                    </span>
                                  )}
                                  {heading}
                                </span>
                                <div className="flex items-center gap-1">
                                  {CHART_TYPES[c.kind].map(ct => {
                                    const CtIcon = TYPE_ICON[ct];
                                    const active = c.type === ct;
                                    return (
                                      <button key={ct} type="button" aria-pressed={active}
                                        title={t(`type${ct[0].toUpperCase()}${ct.slice(1)}`)}
                                        onClick={() => patchChart(c.key, { type: ct })}
                                        className={`cursor-pointer rounded-md border p-1.5 transition-colors
                                          ${active ? 'border-primary bg-primary text-primary-foreground'
                                                   : 'text-muted-foreground hover:border-primary'}`}>
                                        <CtIcon className="h-3.5 w-3.5" />
                                      </button>
                                    );
                                  })}
                                  <button type="button" aria-pressed={c.on}
                                    title={c.on ? t('chartOn') : t('chartOff')}
                                    onClick={() => patchChart(c.key, { on: !c.on })}
                                    className="cursor-pointer rounded-md border p-1.5 text-muted-foreground transition-colors hover:border-primary">
                                    {c.on ? <Eye className="h-3.5 w-3.5" />
                                          : <EyeOff className="h-3.5 w-3.5" />}
                                  </button>
                                </div>
                              </div>
                            );
                          })}
                          {!charts.length && (
                            <p className="text-xs text-muted-foreground">{t('noCharts')}</p>
                          )}
                          {spareDim && (
                            <Button variant="ghost" size="sm" className="gap-1.5 text-xs"
                              onClick={addChart}>
                              <Plus className="h-3.5 w-3.5" />{t('addChart')}
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            {/* ——— الإعدادات: كل ما ليس محتوى التقرير ——— */}
            <Card className="h-fit">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">{t('settings')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('reportTitle')}</Label>
                  <Input dir="auto" value={title} onChange={e => setTitle(e.target.value)} />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">{t('template')}</Label>
                  <div className="grid grid-cols-3 gap-1">
                    {(['executive', 'dashboard', 'detailed'] as const).map(v => (
                      <button key={v} type="button" aria-pressed={template === v}
                        onClick={() => pickTemplate(v)}
                        className={`cursor-pointer rounded-md border px-2 py-1.5 text-xs transition-colors
                          ${template === v ? 'border-primary bg-primary text-primary-foreground'
                                           : 'text-muted-foreground hover:border-primary'}`}>
                        {t(v === 'executive' ? 'tExecutive'
                          : v === 'dashboard' ? 'tDashboard' : 'tDetailed')}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs">{t('language')}</Label>
                  <Select value={language} onValueChange={v => v && setLanguage(v)}>
                    <SelectTrigger className="w-full">
                      <SelectValue>
                        {(v: string) => (v === 'ar' ? t('arabic') : t('english'))}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ar">{t('arabic')}</SelectItem>
                      <SelectItem value="en">{t('english')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {Object.keys(semantics).length > 0 && (
                  <details className="rounded-lg border p-2 text-sm [&[open]>summary]:mb-2">
                    <summary className="cursor-pointer list-none text-xs font-medium">
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
                        {t('advanced')}
                      </span>
                    </summary>
                    <div className="space-y-3">
                      <p className="text-xs text-muted-foreground">{t('autoDetected')}</p>
                      {Object.entries(semantics).map(([table, sem]) => {
                        const ov = overrides[table] ?? {};
                        const measure = ov.measure ?? sem.measures[0] ?? '';
                        const date = ov.date ?? sem.dates[0] ?? '';
                        const setOv = (patch: SemanticOverride) =>
                          setOverrides(o => ({ ...o, [table]: { ...o[table], ...patch } }));
                        return (
                          <div key={table} className="space-y-2 border-t pt-2 first:border-t-0 first:pt-0">
                            {Object.keys(semantics).length > 1 && (
                              <Badge variant="outline" className="font-mono text-xs">{table}</Badge>
                            )}
                            <div className="space-y-1">
                              <Label className="text-xs text-muted-foreground">{t('measureCol')}</Label>
                              <Select value={measure || '—'}
                                onValueChange={v => v && setOv({ measure: v === '—' ? null : v })}>
                                <SelectTrigger className="w-full text-xs">
                                  <SelectValue>
                                    {(v: string) => (v === '—' ? t('none') : lbl(v))}
                                  </SelectValue>
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="—" className="text-xs">{t('none')}</SelectItem>
                                  {sem.measures.map(m => (
                                    <SelectItem key={m} value={m} className="text-xs">{lbl(m)}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            {sem.dates.length > 0 && (
                              <div className="space-y-1">
                                <Label className="text-xs text-muted-foreground">{t('dateCol')}</Label>
                                <Select value={date || '—'}
                                  onValueChange={v => v && setOv({ date: v === '—' ? null : v })}>
                                  <SelectTrigger className="w-full text-xs">
                                    <SelectValue>
                                      {(v: string) => (v === '—' ? t('none') : lbl(v))}
                                    </SelectValue>
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="—" className="text-xs">{t('none')}</SelectItem>
                                    {sem.dates.map(d => (
                                      <SelectItem key={d} value={d} className="text-xs">{lbl(d)}</SelectItem>
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
                                        className={`cursor-pointer rounded-full border px-2.5 py-0.5 text-xs transition-colors
                                          ${on ? 'border-primary bg-primary text-primary-foreground'
                                               : 'text-muted-foreground hover:border-primary'}`}>
                                        {lbl(d)}
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
                          <div className="grid gap-1.5">
                            {usedColumns.map(col => (
                              <Input key={col} dir="auto" className="h-8 text-sm"
                                aria-label={col} title={col}
                                value={labels[col] ?? ''}
                                onChange={e => setLabels(l => ({ ...l, [col]: e.target.value }))} />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </details>
                )}

                <div className="space-y-1.5 border-t pt-3">
                  <Button className="w-full gap-2" onClick={generate}
                    disabled={!selection || generating}>
                    <Sparkles className={`h-4 w-4 ${generating ? 'animate-pulse' : ''}`} />
                    {generating ? t('generating') : t('generate')}
                  </Button>
                  <p className="text-center text-xs text-muted-foreground">
                    {t('willGenerate', {
                      sections: sections.length,
                      charts: sections.includes('charts') ? activeCharts.length : 0,
                    })}
                  </p>
                  {!selection && <p className="text-xs text-destructive">{t('needModel')}</p>}
                  {selection && isSmallModel && (
                    <p className="text-xs text-amber-600 dark:text-amber-500">
                      {t('smallModelWarn')}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
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
