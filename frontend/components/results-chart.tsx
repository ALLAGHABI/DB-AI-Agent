'use client';
import { BarChart3, LineChart as LineIcon } from 'lucide-react';
import { useFormatter, useTranslations } from 'next-intl';
import { useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const MAX_POINTS = 40;

/** رسم بياني فوري من نتائج أي استعلام — يختار المحاور تلقائياً ثم يتيح تغييرها. */
export function ResultsChart({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  const t = useTranslations('chart');
  const format = useFormatter();

  const numericCols = useMemo(
    () => columns.filter((_, i) => rows.some(r => typeof r[i] === 'number')),
    [columns, rows],
  );
  const labelCols = useMemo(
    () => columns.filter(c => !numericCols.includes(c)),
    [columns, numericCols],
  );

  const [xCol, setXCol] = useState(() => labelCols[0] ?? columns[0] ?? '');
  const [yCol, setYCol] = useState(() => numericCols[0] ?? '');
  const [kind, setKind] = useState<'bar' | 'line'>('bar');

  const data = useMemo(() => {
    const xi = columns.indexOf(xCol);
    const yi = columns.indexOf(yCol);
    if (xi < 0 || yi < 0) return [];
    return rows.slice(0, MAX_POINTS).map(r => ({
      name: r[xi] == null ? '—' : String(r[xi]),
      value: typeof r[yi] === 'number' ? (r[yi] as number) : Number(r[yi]) || 0,
    }));
  }, [columns, rows, xCol, yCol]);

  if (!numericCols.length) {
    return <p className="py-10 text-center text-sm text-muted-foreground">{t('needsNumeric')}</p>;
  }

  const axis = { stroke: 'var(--muted-foreground)', fontSize: 11 };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-1">
          <Label className="text-xs">{t('xAxis')}</Label>
          <Select value={xCol} onValueChange={v => v && setXCol(v)}>
            <SelectTrigger className="w-40 font-mono text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              {columns.map(c => (
                <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">{t('yAxis')}</Label>
          <Select value={yCol} onValueChange={v => v && setYCol(v)}>
            <SelectTrigger className="w-40 font-mono text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              {numericCols.map(c => (
                <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-1">
          <Button variant={kind === 'bar' ? 'default' : 'outline'} size="sm"
            className="gap-1.5" onClick={() => setKind('bar')}>
            <BarChart3 className="h-3.5 w-3.5" />{t('bar')}
          </Button>
          <Button variant={kind === 'line' ? 'default' : 'outline'} size="sm"
            className="gap-1.5" onClick={() => setKind('line')}>
            <LineIcon className="h-3.5 w-3.5" />{t('line')}
          </Button>
        </div>
      </div>

      <div dir="ltr" style={{ height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          {kind === 'bar' ? (
            <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="name" {...axis} tickLine={false} interval="preserveStartEnd" />
              <YAxis {...axis} tickLine={false} axisLine={false}
                tickFormatter={v => format.number(v as number)} />
              <Tooltip
                cursor={{ fill: 'var(--muted)' }}
                contentStyle={{ background: 'var(--popover)', border: '1px solid var(--border)',
                  borderRadius: 8, fontSize: 12, color: 'var(--popover-foreground)' }}
                formatter={(v) => format.number(Number(v))} />
              <Bar dataKey="value" fill="var(--primary)" radius={[4, 4, 0, 0]} maxBarSize={44} />
            </BarChart>
          ) : (
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis dataKey="name" {...axis} tickLine={false} interval="preserveStartEnd" />
              <YAxis {...axis} tickLine={false} axisLine={false}
                tickFormatter={v => format.number(v as number)} />
              <Tooltip
                contentStyle={{ background: 'var(--popover)', border: '1px solid var(--border)',
                  borderRadius: 8, fontSize: 12, color: 'var(--popover-foreground)' }}
                formatter={(v) => format.number(Number(v))} />
              <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2}
                dot={false} activeDot={{ r: 5 }} />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
      {rows.length > MAX_POINTS && (
        <p className="text-xs text-muted-foreground">{t('limited', { max: MAX_POINTS })}</p>
      )}
    </div>
  );
}
