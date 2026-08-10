'use client';
import { Bookmark, Plug, Table2, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useApiError } from '@/lib/use-api-error';
import { api, type SavedConnection } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

type DbType = 'sqlite' | 'mysql' | 'postgresql';

export function ConnectionsPanel({ onConnected }: { onConnected: (tables: string[]) => void }) {
  const t = useTranslations('connections');
  const { showError } = useApiError();
  const [type, setType] = useState<DbType>('sqlite');
  const [sqlitePath, setSqlitePath] = useState('data/sample_store.db');
  const [server, setServer] = useState({ host: 'localhost', port: '', database: '', username: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [tables, setTables] = useState<string[]>([]);
  const [saved, setSaved] = useState<SavedConnection[]>([]);
  const [saveName, setSaveName] = useState('');

  const loadSaved = useCallback(async () => {
    try { setSaved(await api.connectionsList()); } catch { /* قائمة فارغة تكفي */ }
  }, []);
  useEffect(() => { loadSaved(); }, [loadSaved]);

  const saveConnection = async () => {
    if (!saveName.trim()) return;
    try {
      await api.connectionAdd({
        name: saveName.trim(), type,
        sqlite_file: type === 'sqlite' ? sqlitePath.trim() : '',
        host: server.host, port: server.port, database: server.database,
        username: server.username, password: server.password,
      });
      setSaveName('');
      toast.success(t('saved_ok'));
      loadSaved();
    } catch (e) { showError(e); }
  };

  const useConnection = async (conn: SavedConnection) => {
    setBusy(true);
    try {
      const res = await api.connectionUse(conn.id);
      setTables(res.tables);
      onConnected(res.tables);
      toast.success(t('connectSuccess'));
    } catch (e) { showError(e); } finally { setBusy(false); }
  };

  const removeConnection = async (id: string) => {
    try { await api.connectionDelete(id); loadSaved(); } catch (e) { showError(e); }
  };

  const buildUrl = () => {
    if (type === 'sqlite') return `sqlite:///${sqlitePath.trim()}`;
    const port = server.port || (type === 'mysql' ? '3306' : '5432');
    const driver = type === 'mysql' ? 'mysql+pymysql' : 'postgresql+psycopg';
    return `${driver}://${server.username}:${server.password}@${server.host}:${port}/${server.database}`;
  };

  const connect = async () => {
    setBusy(true);
    try {
      const res = await api.connect(buildUrl());
      setTables(res.tables);
      onConnected(res.tables);
      toast.success(t('connectSuccess'));
    } catch (e) {
      showError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{t('title')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label className="text-xs">{t('type')}</Label>
          <Select value={type} onValueChange={v => setType(v as DbType)}>
            <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="sqlite">SQLite</SelectItem>
              <SelectItem value="mysql">MySQL</SelectItem>
              <SelectItem value="postgresql">PostgreSQL</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {type === 'sqlite' ? (
          <div className="space-y-1.5">
            <Label className="text-xs">{t('sqlitePath')}</Label>
            <Input dir="ltr" value={sqlitePath} onChange={e => setSqlitePath(e.target.value)} />
            <Button variant="link" size="sm" className="h-auto p-0 text-xs"
              onClick={() => setSqlitePath('data/sample_store.db')}>
              {t('sample')}
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1.5"><Label className="text-xs">{t('host')}</Label>
              <Input dir="ltr" value={server.host} onChange={e => setServer({ ...server, host: e.target.value })} /></div>
            <div className="space-y-1.5"><Label className="text-xs">{t('port')}</Label>
              <Input dir="ltr" value={server.port} placeholder={type === 'mysql' ? '3306' : '5432'}
                onChange={e => setServer({ ...server, port: e.target.value })} /></div>
            <div className="col-span-2 space-y-1.5"><Label className="text-xs">{t('database')}</Label>
              <Input dir="ltr" value={server.database} onChange={e => setServer({ ...server, database: e.target.value })} /></div>
            <div className="space-y-1.5"><Label className="text-xs">{t('username')}</Label>
              <Input dir="ltr" value={server.username} onChange={e => setServer({ ...server, username: e.target.value })} /></div>
            <div className="space-y-1.5"><Label className="text-xs">{t('password')}</Label>
              <Input dir="ltr" type="password" value={server.password} onChange={e => setServer({ ...server, password: e.target.value })} /></div>
          </div>
        )}

        <Button className="w-full" onClick={connect} disabled={busy}>
          {busy ? t('connecting') : t('connect')}
        </Button>

        <div className="space-y-1.5 border-t pt-3">
          <Label className="text-xs">{t('save')}</Label>
          <div className="flex gap-1.5">
            <Input dir="auto" value={saveName} placeholder={t('saveName')}
              onChange={e => setSaveName(e.target.value)} />
            <Button variant="secondary" size="icon" aria-label={t('save')}
              onClick={saveConnection} disabled={!saveName.trim()}>
              <Bookmark className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {saved.length > 0 && (
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">{t('saved')}</Label>
            <ul className="space-y-1">
              {saved.map(c => (
                <li key={c.id} className="flex items-center gap-1 rounded-lg border px-2 py-1.5">
                  <span className="min-w-0 flex-1 truncate text-xs" dir="auto">
                    {c.name}
                    <span className="ms-1.5 font-mono text-[10px] text-muted-foreground">{c.type}</span>
                  </span>
                  <Button variant="ghost" size="icon" className="h-6 w-6" aria-label={t('use')}
                    onClick={() => useConnection(c)} disabled={busy}>
                    <Plug className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                    aria-label={t('remove')} onClick={() => removeConnection(c.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {tables.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <Label className="text-xs text-muted-foreground">{t('connectedTables')}</Label>
            <div className="flex flex-wrap gap-1.5">
              {tables.map(tb => (
                <Badge key={tb} variant="outline" className="gap-1 font-mono text-xs">
                  <Table2 className="h-3 w-3" />{tb}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
