'use client';
import { Play, Star, Trash2 } from 'lucide-react';
import { useFormatter, useTranslations } from 'next-intl';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, type HistoryEntry } from '@/lib/api';
import { useApiError } from '@/lib/use-api-error';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

/** سجل الاستعلامات — إعادة تشغيل بنقرة، وتمييز المفضلة. */
export function HistoryPanel({ onReuse }: { onReuse: (entry: HistoryEntry) => void }) {
  const t = useTranslations('history');
  const format = useFormatter();
  const { showError } = useApiError();
  const [items, setItems] = useState<HistoryEntry[]>([]);
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await api.historyList(favoritesOnly));
    } catch (e) { showError(e); }
  }, [favoritesOnly, showError]);

  useEffect(() => { load(); }, [load]);

  const toggleFavorite = async (entry: HistoryEntry) => {
    try {
      await api.historyFavorite(entry.id, !entry.favorite);
      setItems(list => list.map(i =>
        i.id === entry.id ? { ...i, favorite: !i.favorite } : i));
    } catch (e) { showError(e); }
  };

  const remove = async (id: number) => {
    try {
      await api.historyDelete(id);
      setItems(list => list.filter(i => i.id !== id));
    } catch (e) { showError(e); }
  };

  const clearAll = async () => {
    try {
      const res = await api.historyClear();
      toast.success(t('cleared', { count: res.removed }));
      load();
    } catch (e) { showError(e); }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-sm">{t('title')}</CardTitle>
          <div className="flex items-center gap-1.5">
            <Button variant={favoritesOnly ? 'default' : 'outline'} size="sm" className="gap-1.5"
              onClick={() => setFavoritesOnly(v => !v)}>
              <Star className="h-3.5 w-3.5" />{t('favoritesOnly')}
            </Button>
            <Button variant="ghost" size="sm" className="gap-1.5 text-destructive"
              onClick={clearAll} disabled={!items.length}>
              <Trash2 className="h-3.5 w-3.5" />{t('clear')}
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{t('hint')}</p>
      </CardHeader>
      <CardContent>
        {!items.length ? (
          <p className="py-10 text-center text-sm text-muted-foreground">{t('empty')}</p>
        ) : (
          <ul className="divide-y">
            {items.map(entry => (
              <li key={entry.id} className="flex items-start gap-2 py-2.5">
                <div className="min-w-0 flex-1 space-y-1">
                  {entry.request && (
                    <p className="truncate text-sm font-medium" dir="auto">{entry.request}</p>
                  )}
                  <pre dir="ltr"
                    className="truncate rounded bg-muted px-2 py-1 font-mono text-xs">{entry.sql}</pre>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{format.dateTime(new Date(entry.created_at),
                      { dateStyle: 'short', timeStyle: 'short' })}</span>
                    {entry.model && <Badge variant="outline" className="font-mono text-[10px]">{entry.model}</Badge>}
                    {!entry.success && <Badge variant="destructive" className="text-[10px]">{t('failed')}</Badge>}
                    {entry.success && entry.rows > 0 && <span>{t('rows', { count: entry.rows })}</span>}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-0.5">
                  <Button variant="ghost" size="icon" className="h-7 w-7"
                    aria-label={t('reuse')} onClick={() => onReuse(entry)}>
                    <Play className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7"
                    aria-label={t('favorite')} onClick={() => toggleFavorite(entry)}>
                    <Star className={`h-3.5 w-3.5 ${entry.favorite ? 'fill-primary text-primary' : ''}`} />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                    aria-label={t('delete')} onClick={() => remove(entry.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
