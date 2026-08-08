'use client';
import { Cloud, Cpu, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, type ProviderStatus } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

export type ModelSelection = { provider: string; model: string; isLocal: boolean };

export function ProvidersPanel({ onModelChange }: { onModelChange: (s: ModelSelection | null) => void }) {
  const t = useTranslations('settings');
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [selected, setSelected] = useState<ModelSelection | null>(null);
  const [orKey, setOrKey] = useState('');
  const [hasOrKey, setHasOrKey] = useState(false);
  const [compatUrl, setCompatUrl] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [ps, st] = await Promise.all([api.providers(), api.settings()]);
      setProviders(ps);
      setHasOrKey(st.has_openrouter_api_key);
      setCompatUrl(st.openai_compat_url);
      // اختيار افتراضي: أول مزود محلي متاح وأول نموذج له
      setSelected(prev => {
        if (prev) {
          const p = ps.find(x => x.id === prev.provider);
          if (p?.available && (p.models.includes(prev.model) || p.id === 'openrouter')) return prev;
        }
        const local = ps.find(p => p.is_local && p.available && p.models.length);
        const any = local ?? ps.find(p => p.available && p.models.length);
        return any ? { provider: any.id, model: any.models[0], isLocal: any.is_local } : null;
      });
    } catch (e) {
      toast.error((e as Error).message);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { onModelChange(selected); }, [selected, onModelChange]);

  const saveSecrets = async () => {
    setBusy(true);
    try {
      await api.saveSecrets({
        ...(orKey ? { openrouter_api_key: orKey } : {}),
        openai_compat_url: compatUrl,
      });
      setOrKey('');
      toast.success(t('saved'));
      await refresh();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const current = providers.find(p => p.id === selected?.provider);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{t('title')}</CardTitle>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={refresh} aria-label={t('refresh')}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">{t('localFirst')}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1.5">
          <Label className="text-xs">{t('provider')}</Label>
          <div className="space-y-1.5">
            {providers.map(p => (
              <button key={p.id} type="button"
                onClick={() => p.available && p.models.length &&
                  setSelected({ provider: p.id, model: p.models[0], isLocal: p.is_local })}
                className={`flex w-full cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-start text-xs transition-colors
                  ${selected?.provider === p.id ? 'border-primary bg-accent' : 'hover:bg-muted'}
                  ${!p.available ? 'opacity-50' : ''}`}>
                <span className="flex items-center gap-2">
                  {p.is_local ? <Cpu className="h-3.5 w-3.5 text-primary" /> : <Cloud className="h-3.5 w-3.5" />}
                  {p.label}
                </span>
                <span className={`h-2 w-2 rounded-full ${p.available ? 'bg-primary' : 'bg-muted-foreground/40'}`} />
              </button>
            ))}
          </div>
          {providers.find(p => p.id === 'ollama' && !p.available) && (
            <p className="text-xs text-destructive" dir="ltr">{t('ollamaMissing')}</p>
          )}
        </div>

        {current && current.models.length > 0 && selected && (
          <div className="space-y-1.5">
            <Label className="text-xs">{t('model')}</Label>
            <Select value={selected.model}
              onValueChange={m => m && setSelected({ ...selected, model: m })}>
              <SelectTrigger className="w-full font-mono text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                {current.models.map(m => (
                  <SelectItem key={m} value={m} className="font-mono text-xs">{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="space-y-2 border-t pt-3">
          <div className="space-y-1.5">
            <Label className="text-xs">{t('openrouterKey')}</Label>
            <Input dir="ltr" type="password" value={orKey}
              placeholder={hasOrKey ? '••••••••' : 'sk-or-v1-…'}
              onChange={e => setOrKey(e.target.value)} />
            {hasOrKey && <p className="text-xs text-muted-foreground">{t('keySaved')}</p>}
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">{t('compatUrl')}</Label>
            <Input dir="ltr" value={compatUrl ?? ''} placeholder="http://localhost:1234/v1"
              onChange={e => setCompatUrl(e.target.value)} />
          </div>
          <Button variant="secondary" size="sm" className="w-full" onClick={saveSecrets} disabled={busy}>
            {t('save')}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
