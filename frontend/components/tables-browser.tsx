'use client';
import {
  ArrowUpDown, ChevronLeft, ChevronRight, Download, FileBarChart, HardDriveDownload, KeyRound,
  Loader2, Plus, Trash2, Upload,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { useApiError } from '@/lib/use-api-error';
import { api, type BrowseResult } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

const PAGE = 50;

export function TablesBrowser({ tables, dialect, onSchemaChanged, onReportFromTable }: {
  tables: string[]; dialect: string | null; onSchemaChanged: () => void;
  onReportFromTable: (table: string) => void;
}) {
  const t = useTranslations('tables');
  const locale = useLocale();
  const { showError } = useApiError();
  const [table, setTable] = useState<string>('');
  const [data, setData] = useState<BrowseResult | null>(null);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<{ col: string; dir: 'asc' | 'desc' } | null>(null);
  const [editing, setEditing] = useState<{ row: number; col: string; value: string } | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [addValues, setAddValues] = useState<Record<string, string>>({});
  const [importOpen, setImportOpen] = useState(false);
  const [importTable, setImportTable] = useState('');
  const [importMode, setImportMode] = useState<'create' | 'append'>('create');
  const fileRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [importFileName, setImportFileName] = useState('');
  const reqId = useRef(0);

  const load = useCallback(async (tb: string, pg: number, srt: typeof sort) => {
    if (!tb) return;
    const id = ++reqId.current;
    setLoading(true);
    try {
      const res = await api.tableRows(tb, {
        limit: PAGE, offset: pg * PAGE,
        orderBy: srt?.col, dir: srt?.dir,
      });
      if (id !== reqId.current) return;      // استجابة قديمة — تجاهلها
      setData(res);
      setSelected(new Set());
    } catch (e) {
      if (id === reqId.current) showError(e);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, [showError]);

  useEffect(() => { load(table, page, sort); }, [table, page, sort, load]);
  useEffect(() => {
    if (tables.length && !tables.includes(table)) { setTable(tables[0]); setPage(0); setSort(null); }
  }, [tables, table]);

  const pkOf = (rowIdx: number): Record<string, unknown> | null => {
    if (!data || !data.primary_keys.length) return null;
    const row = data.rows[rowIdx];
    return Object.fromEntries(data.primary_keys.map(k => [k, row[data.columns.indexOf(k)]]));
  };

  const saveEdit = async () => {
    if (!editing || !data || mutating) return;
    const pk = pkOf(editing.row);
    if (!pk) { toast.error(t('noPk')); setEditing(null); return; }
    const cell = editing;
    setMutating(true);
    try {
      await api.updateRow(table, pk, { [cell.col]: cell.value });
      toast.success(t('saved'));
      setEditing(null);
      await load(table, page, sort);
      // إعادة التركيز إلى الخلية بعد الحفظ (إتاحة الكيبورد)
      requestAnimationFrame(() =>
        document.querySelector<HTMLElement>(
          `[data-cell="${cell.row}-${cell.col}"]`)?.focus());
    } catch (e) { showError(e); } finally { setMutating(false); }
  };

  const deleteSelected = async () => {
    if (mutating) return;
    setMutating(true);
    const targets = [...selected].map(pkOf).filter(Boolean) as Record<string, unknown>[];
    const results = await Promise.allSettled(
      targets.map(pk => api.deleteRow(table, pk)));
    const ok = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.find(r => r.status === 'rejected');
    setConfirmDelete(false);
    setMutating(false);
    if (ok) toast.success(t('deletedCount', { ok, total: targets.length }));
    if (failed) showError((failed as PromiseRejectedResult).reason);
    await load(table, page, sort);
  };

  const addRow = async () => {
    if (mutating) return;
    const values = Object.fromEntries(
      Object.entries(addValues).filter(([, v]) => v !== ''));
    setMutating(true);
    try {
      await api.insertRow(table, values);
      toast.success(t('added'));
      setAddOpen(false); setAddValues({});
      await load(table, page, sort);
    } catch (e) { showError(e); } finally { setMutating(false); }
  };

  const runImport = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !importTable || mutating) return;
    setMutating(true);
    try {
      const res = await api.importFile(file, importTable, importMode);
      toast.success(t('imported', { count: res.inserted, table: res.table }));
      setImportOpen(false);
      setImportFileName('');
      onSchemaChanged();       // تحديث قائمة الجداول بلا إعادة تحميل الصفحة
    } catch (e) { showError(e); } finally { setMutating(false); }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE)) : 1;
  const canEdit = !!data?.primary_keys.length;
  const PrevIcon = locale === 'ar' ? ChevronRight : ChevronLeft;
  const NextIcon = locale === 'ar' ? ChevronLeft : ChevronRight;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Select value={table} onValueChange={v => { if (v) { setTable(v); setPage(0); setSort(null); } }}>
            <SelectTrigger className="w-48 font-mono text-xs"><SelectValue placeholder={t('pick')} /></SelectTrigger>
            <SelectContent>
              {tables.map(tb => <SelectItem key={tb} value={tb} className="font-mono text-xs">{tb}</SelectItem>)}
            </SelectContent>
          </Select>
          {table && <div className="ms-auto flex flex-wrap items-center gap-1.5">
            <Button variant="outline" size="sm" className="gap-1.5" disabled={!canEdit || mutating}
              onClick={() => { setAddValues({}); setAddOpen(true); }}>
              <Plus className="h-3.5 w-3.5" />{t('addRow')}
            </Button>
            {canEdit && selected.size > 0 && (
              <Button variant="outline" size="sm" className="gap-1.5 text-destructive"
                disabled={mutating} onClick={() => setConfirmDelete(true)}>
                <Trash2 className="h-3.5 w-3.5" />{t('deleteSelected')} ({selected.size})
              </Button>
            )}
            <Button variant="outline" size="sm" className="gap-1.5"
              onClick={() => onReportFromTable(table)}>
              <FileBarChart className="h-3.5 w-3.5" />{t('reportFromTable')}
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5"
              onClick={() => { window.location.href = api.exportUrl(table, 'csv'); }}>
              <Download className="h-3.5 w-3.5" />{t('exportCsv')}
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5"
              onClick={() => { window.location.href = api.exportUrl(table, 'xlsx'); }}>
              <Download className="h-3.5 w-3.5" />{t('exportXlsx')}
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5"
              onClick={() => { setImportTable(''); setImportOpen(true); }}>
              <Upload className="h-3.5 w-3.5" />{t('import')}
            </Button>
            {dialect === 'sqlite' && (
              <Button variant="outline" size="sm" className="gap-1.5"
                onClick={() => { window.location.href = api.backupUrl(); }}>
                <HardDriveDownload className="h-3.5 w-3.5" />{t('backup')}
              </Button>
            )}
          </div>}
        </div>
        {canEdit
          ? <p className="text-xs text-muted-foreground">{t('editHint')}</p>
          : data && <Badge variant="secondary" className="w-fit text-xs">{t('noPk')}</Badge>}
      </CardHeader>
      <CardContent>
        {!tables.length && (
          <p className="py-12 text-center text-sm text-muted-foreground">{t('needsConnection')}</p>
        )}
        {data && (
          <>
            <div className={`max-h-[520px] overflow-auto rounded-lg border transition-opacity ${loading ? 'opacity-50' : ''}`}>
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    {canEdit && <TableHead className="w-8">
                      <input type="checkbox" className="size-4 cursor-pointer"
                        aria-label={t('selectAll')}
                        ref={el => { if (el) el.indeterminate =
                          selected.size > 0 && selected.size < data.rows.length; }}
                        checked={selected.size === data.rows.length && data.rows.length > 0}
                        onChange={e => setSelected(e.target.checked
                          ? new Set(data.rows.map((_, i) => i)) : new Set())} />
                    </TableHead>}
                    {data.columns.map(c => (
                      <TableHead key={c}
                        aria-sort={sort?.col === c
                          ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                        <button type="button"
                          className="flex cursor-pointer items-center gap-1 font-mono text-xs font-semibold"
                          onClick={() => setSort(s =>
                            s?.col === c && s.dir === 'asc' ? { col: c, dir: 'desc' } : { col: c, dir: 'asc' })}>
                          {c}
                          {data.primary_keys.includes(c) && (
                            <><KeyRound className="h-3 w-3 text-primary" aria-hidden />
                              <span className="sr-only">{t('primaryKey')}</span></>
                          )}
                          <ArrowUpDown className="h-3 w-3 opacity-50" />
                        </button>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.rows.map((row, ri) => (
                    <TableRow key={ri} data-state={selected.has(ri) ? 'selected' : undefined}>
                      {canEdit && <TableCell className="w-8">
                        <input type="checkbox" className="size-4 cursor-pointer"
                          aria-label={t('selectRow', { n: ri + 1 })} checked={selected.has(ri)}
                          onChange={e => {
                            const next = new Set(selected);
                            if (e.target.checked) next.add(ri); else next.delete(ri);
                            setSelected(next);
                          }} />
                      </TableCell>}
                      {data.columns.map((c, ci) => {
                        const isEditing = editing?.row === ri && editing?.col === c;
                        const v = row[ci];
                        const editable = canEdit && !data.primary_keys.includes(c);
                        const startEdit = () => setEditing(
                          { row: ri, col: c, value: v == null ? '' : String(v) });
                        return (
                          <TableCell key={c} className="text-sm">
                            {isEditing ? (
                              <Input autoFocus dir="auto" className="h-7 min-w-24 text-sm"
                                aria-label={c}
                                value={editing.value}
                                onChange={e => setEditing({ ...editing, value: e.target.value })}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') { e.preventDefault(); saveEdit(); }
                                  if (e.key === 'Escape') { e.preventDefault(); setEditing(null); }
                                }}
                                onBlur={saveEdit} />
                            ) : editable ? (
                              <span role="button" tabIndex={0} data-cell={`${ri}-${c}`}
                                className="inline-block min-w-8 cursor-text rounded px-1 outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                                onDoubleClick={startEdit}
                                onKeyDown={e => {
                                  if (e.key === 'Enter' || e.key === 'F2') { e.preventDefault(); startEdit(); }
                                }}>
                                <bdi>{v == null ? <span className="text-muted-foreground">—</span> : String(v)}</bdi>
                              </span>
                            ) : (
                              <bdi>{v == null ? <span className="text-muted-foreground">—</span> : String(v)}</bdi>
                            )}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex items-center justify-between pt-2 text-xs text-muted-foreground">
              <span>{t('rowCount', { count: data.total })}</span>
              <div className="flex items-center gap-1.5">
                <Button variant="ghost" size="sm" disabled={page === 0 || loading}
                  onClick={() => setPage(p => p - 1)}>
                  <PrevIcon className="h-4 w-4" />{t('prev')}
                </Button>
                <span>{page + 1} / {totalPages}</span>
                <Button variant="ghost" size="sm" disabled={page + 1 >= totalPages || loading}
                  onClick={() => setPage(p => p + 1)}>
                  {t('next')}<NextIcon className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </CardContent>

      {/* حذف محدد */}
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('deleteConfirmTitle')}</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">{t('deleteConfirmBody', { count: selected.size })}</p>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirmDelete(false)}>{t('cancel')}</Button>
            <Button variant="destructive" onClick={deleteSelected} disabled={mutating}>
              {mutating && <Loader2 className="h-4 w-4 animate-spin" />}{t('deleteSelected')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* إضافة صف */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{t('addRow')} — {table}</DialogTitle></DialogHeader>
          <div className="space-y-2">
            {data?.columns.filter(c => !data.primary_keys.includes(c)).map(c => (
              <div key={c} className="space-y-1">
                <Label className="font-mono text-xs">{c}</Label>
                <Input dir="auto" value={addValues[c] ?? ''}
                  onChange={e => setAddValues({ ...addValues, [c]: e.target.value })} />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button onClick={addRow} disabled={mutating}>
              {mutating && <Loader2 className="h-4 w-4 animate-spin" />}{t('add')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* استيراد */}
      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('importTitle')}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-xs" htmlFor="import-file">{t('importFile')}</Label>
              <Input id="import-file" ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.json"
                className="cursor-pointer"
                onChange={e => setImportFileName(e.target.files?.[0]?.name ?? '')} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t('importTable')}</Label>
              <Input dir="ltr" value={importTable} onChange={e => setImportTable(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">{t('importMode')}</Label>
              <Select value={importMode} onValueChange={v => v && setImportMode(v as 'create' | 'append')}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="create">{t('importCreate')}</SelectItem>
                  <SelectItem value="append">{t('importAppend')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={runImport} disabled={!importTable || !importFileName || mutating}>
              {mutating && <Loader2 className="h-4 w-4 animate-spin" />}{t('importRun')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
