'use client';
import {
  ArrowUpDown, ChevronLeft, ChevronRight, Download, HardDriveDownload, Plus, Trash2, Upload,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
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

export function TablesBrowser({ tables, dialect }: { tables: string[]; dialect: string | null }) {
  const t = useTranslations('tables');
  const locale = useLocale();
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

  const load = useCallback(async (tb: string, pg: number, srt: typeof sort) => {
    if (!tb) return;
    try {
      const res = await api.tableRows(tb, {
        limit: PAGE, offset: pg * PAGE,
        orderBy: srt?.col, dir: srt?.dir,
      });
      setData(res);
      setSelected(new Set());
    } catch (e) {
      toast.error((e as Error).message);
    }
  }, []);

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
    if (!editing || !data) return;
    const pk = pkOf(editing.row);
    if (!pk) { toast.error(t('noPk')); setEditing(null); return; }
    try {
      await api.updateRow(table, pk, { [editing.col]: editing.value });
      toast.success(t('saved'));
      setEditing(null);
      load(table, page, sort);
    } catch (e) { toast.error((e as Error).message); }
  };

  const deleteSelected = async () => {
    setConfirmDelete(false);
    try {
      for (const idx of selected) {
        const pk = pkOf(idx);
        if (pk) await api.deleteRow(table, pk);
      }
      toast.success(t('deleted'));
      load(table, page, sort);
    } catch (e) { toast.error((e as Error).message); }
  };

  const addRow = async () => {
    const values = Object.fromEntries(
      Object.entries(addValues).filter(([, v]) => v !== ''));
    try {
      await api.insertRow(table, values);
      toast.success(t('added'));
      setAddOpen(false); setAddValues({});
      load(table, page, sort);
    } catch (e) { toast.error((e as Error).message); }
  };

  const runImport = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !importTable) return;
    try {
      const res = await api.importFile(file, importTable, importMode);
      toast.success(t('imported', { count: res.inserted, table: res.table }));
      setImportOpen(false);
      location.reload();      // لتحديث قائمة الجداول من المصدر
    } catch (e) { toast.error((e as Error).message); }
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
          <div className="ms-auto flex flex-wrap items-center gap-1.5">
            <Button variant="outline" size="sm" className="gap-1.5" disabled={!canEdit}
              onClick={() => { setAddValues({}); setAddOpen(true); }}>
              <Plus className="h-3.5 w-3.5" />{t('addRow')}
            </Button>
            <Button variant="outline" size="sm" className="gap-1.5 text-destructive"
              disabled={!selected.size || !canEdit} onClick={() => setConfirmDelete(true)}>
              <Trash2 className="h-3.5 w-3.5" />{t('deleteSelected')} {selected.size ? `(${selected.size})` : ''}
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
          </div>
        </div>
        {canEdit
          ? <p className="text-xs text-muted-foreground">{t('editHint')}</p>
          : data && <Badge variant="secondary" className="w-fit text-xs">{t('noPk')}</Badge>}
      </CardHeader>
      <CardContent>
        {data && (
          <>
            <div className="max-h-[520px] overflow-auto rounded-lg border">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    {canEdit && <TableHead className="w-8">
                      <input type="checkbox" className="cursor-pointer"
                        checked={selected.size === data.rows.length && data.rows.length > 0}
                        onChange={e => setSelected(e.target.checked
                          ? new Set(data.rows.map((_, i) => i)) : new Set())} />
                    </TableHead>}
                    {data.columns.map(c => (
                      <TableHead key={c}>
                        <button type="button"
                          className="flex cursor-pointer items-center gap-1 font-mono text-xs font-semibold"
                          onClick={() => setSort(s =>
                            s?.col === c && s.dir === 'asc' ? { col: c, dir: 'desc' } : { col: c, dir: 'asc' })}>
                          {c}
                          {data.primary_keys.includes(c) && <span title="PK">🔑</span>}
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
                        <input type="checkbox" className="cursor-pointer" checked={selected.has(ri)}
                          onChange={e => {
                            const next = new Set(selected);
                            if (e.target.checked) next.add(ri); else next.delete(ri);
                            setSelected(next);
                          }} />
                      </TableCell>}
                      {data.columns.map((c, ci) => {
                        const isEditing = editing?.row === ri && editing?.col === c;
                        const v = row[ci];
                        return (
                          <TableCell key={c} className="text-sm"
                            onDoubleClick={() => canEdit && !data.primary_keys.includes(c) &&
                              setEditing({ row: ri, col: c, value: v == null ? '' : String(v) })}>
                            {isEditing ? (
                              <Input autoFocus dir="auto" className="h-7 min-w-24 text-sm"
                                value={editing.value}
                                onChange={e => setEditing({ ...editing, value: e.target.value })}
                                onKeyDown={e => {
                                  if (e.key === 'Enter') saveEdit();
                                  if (e.key === 'Escape') setEditing(null);
                                }}
                                onBlur={() => setEditing(null)} />
                            ) : v == null ? <span className="text-muted-foreground">—</span> : String(v)}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex items-center justify-between pt-2 text-xs text-muted-foreground">
              <span>{data.total} {t('rows')}</span>
              <div className="flex items-center gap-1.5">
                <Button variant="ghost" size="sm" disabled={page === 0}
                  onClick={() => setPage(p => p - 1)}>
                  <PrevIcon className="h-4 w-4" />{t('prev')}
                </Button>
                <span>{page + 1} / {totalPages}</span>
                <Button variant="ghost" size="sm" disabled={page + 1 >= totalPages}
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
            <Button variant="destructive" onClick={deleteSelected}>{t('deleteSelected')}</Button>
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
            <Button onClick={addRow}>{t('add')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* استيراد */}
      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t('importTitle')}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.json" className="cursor-pointer" />
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
            <Button onClick={runImport} disabled={!importTable}>{t('importRun')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
