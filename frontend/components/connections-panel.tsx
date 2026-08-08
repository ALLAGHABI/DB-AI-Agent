'use client';
import { Table2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
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
  const [type, setType] = useState<DbType>('sqlite');
  const [sqlitePath, setSqlitePath] = useState('data/sample_store.db');
  const [server, setServer] = useState({ host: 'localhost', port: '', database: '', username: '', password: '' });
  const [busy, setBusy] = useState(false);
  const [tables, setTables] = useState<string[]>([]);

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
      toast.error((e as Error).message);
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
