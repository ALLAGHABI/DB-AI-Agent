'use client';
import {
  Cloud, Cpu, Download, ExternalLink, FileSpreadsheet, FileText, Sparkles, Trash2, Upload,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { api, type ReportMeta, type ReportProfile } from '@/lib/api';
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
import type { ModelSelection } from './providers-panel';

export function ReportsStudio({ selection }: { selection: ModelSelection | null }) {
  const t = useTranslations('reports');
  const locale = useLocale();
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

  useEffect(() => { api.reportsList().then(setReports).catch(() => {}); }, []);

  const analyze = async (file: File) => {
    setAnalyzing(true);
    setProfile(null); setToken(null);
    try {
      const res = await api.reportAnalyze(file);
      setToken(res.token);
      setProfile(res.profile);
      setSourceName(file.name);
      if (!title) setTitle(file.name.replace(/\.[^.]+$/, ''));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  const generate = async () => {
    if (!token || !selection) return;
    setGenerating(true);
    try {
      const meta = await api.reportGenerate({
        token, title: title || sourceName, template, language,
        provider: selection.provider, model: selection.model,
      });
      setReports(r => [meta, ...r]);
      toast.success(t('generated'));
      window.open(api.reportFileUrl(meta.id, 'html'), '_blank');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  const remove = async () => {
    if (!deleteId) return;
    try {
      await api.reportDelete(deleteId);
      setReports(r => r.filter(x => x.id !== deleteId));
    } catch (e) { toast.error((e as Error).message); }
    setDeleteId(null);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">{t('title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <button type="button"
            className="flex w-full cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed p-8 text-sm text-muted-foreground transition-colors hover:border-primary hover:bg-accent/40"
            onClick={() => fileRef.current?.click()}>
            <Upload className="h-6 w-6" />
            {analyzing ? t('analyzing') : t('uploadHint')}
            <span className="text-xs">{sourceName || t('pickFile')}</span>
          </button>
          <input ref={fileRef} type="file" hidden accept=".csv,.xlsx,.xls,.json"
            onChange={e => e.target.files?.[0] && analyze(e.target.files[0])} />

          {profile && (
            <>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  [profile.overview.rows.toLocaleString(), t('rows')],
                  [String(profile.overview.cols), t('cols')],
                  [`${profile.overview.missing_pct}%`, t('missing')],
                  [String(profile.overview.duplicate_rows), t('duplicates')],
                ].map(([v, l]) => (
                  <div key={l} className="rounded-lg border bg-muted/40 p-3 text-center">
                    <div className="text-xl font-bold tabular-nums">{v}</div>
                    <div className="text-xs text-muted-foreground">{l}</div>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {profile.columns.map(c => (
                  <Badge key={c.name} variant="outline" className="font-mono text-xs">
                    {c.name} <span className="text-muted-foreground">· {c.kind}</span>
                  </Badge>
                ))}
              </div>

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
            </>
          )}
        </CardContent>
      </Card>

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
                        {r.source_name} · {r.rows.toLocaleString()} × {r.cols} · {r.created_at}
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

      <Dialog open={!!deleteId} onOpenChange={o => !o && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('deleteConfirm')}</DialogTitle></DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDeleteId(null)}>{t('cancel')}</Button>
            <Button variant="destructive" onClick={remove}>{t('delete')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
