'use client';
import {
  Background, Controls, Handle, Position, ReactFlow,
  type Edge, type Node, type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { KeyRound, Link2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useApiError } from '@/lib/use-api-error';
import { api, type TableSchema } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

type TableNodeData = { table: TableSchema; rowsLabel: string };

function TableNode({ data }: NodeProps) {
  const { table, rowsLabel } = data as unknown as TableNodeData;
  const fkCols = new Set(table.foreign_keys.flatMap(fk => fk.constrained_columns));
  return (
    <div dir="ltr" className="min-w-48 overflow-hidden rounded-xl border bg-card text-card-foreground shadow-md">
      <Handle type="target" position={Position.Left} className="opacity-0" />
      <Handle type="source" position={Position.Right} className="opacity-0" />
      <div className="flex items-center justify-between bg-primary/10 px-3 py-2">
        <span className="font-mono text-sm font-bold">{table.name}</span>
        <span className="text-xs text-muted-foreground">{table.row_count} {rowsLabel}</span>
      </div>
      <ul className="divide-y">
        {table.columns.map(c => (
          <li key={c.name} className="flex items-center justify-between gap-3 px-3 py-1 text-xs">
            <span className="flex items-center gap-1.5 font-mono">
              {table.primary_keys.includes(c.name) && <KeyRound className="h-3 w-3 text-primary" />}
              {fkCols.has(c.name) && <Link2 className="h-3 w-3 text-sky-500" />}
              {c.name}
            </span>
            <span className="text-muted-foreground">{c.type.toLowerCase()}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const nodeTypes = { table: TableNode };

export function ErDiagram({ connected }: { connected: boolean }) {
  const t = useTranslations('er');
  const [tables, setTables] = useState<TableSchema[]>([]);
  const [failed, setFailed] = useState(false);
  const { showError } = useApiError();

  const load = useCallback(async () => {
    if (!connected) { setTables([]); setFailed(false); return; }
    try {
      const s = await api.schema();
      setTables(s.tables);
      setFailed(false);
    } catch (e) {
      setFailed(true);
      showError(e);
    }
  }, [connected, showError]);

  useEffect(() => { load(); }, [load]);

  const { nodes, edges } = useMemo(() => {
    const COLS = 3, W = 300, H = 280;
    const nodes: Node[] = tables.map((tb, i) => ({
      id: tb.name,
      type: 'table',
      position: { x: (i % COLS) * W, y: Math.floor(i / COLS) * H },
      data: { table: tb, rowsLabel: t('rows') } as unknown as Record<string, unknown>,
    }));
    const edges: Edge[] = tables.flatMap(tb =>
      tb.foreign_keys.map((fk, j) => ({
        id: `${tb.name}-${fk.referred_table}-${j}`,
        source: tb.name,
        target: fk.referred_table,
        type: 'smoothstep',
        label: fk.constrained_columns.join(','),
        animated: true,
        style: { strokeWidth: 1.5, stroke: 'var(--muted-foreground)' },
        labelStyle: { fontSize: 10, fontFamily: 'monospace', fill: 'var(--foreground)' },
        labelBgStyle: { fill: 'var(--card)', fillOpacity: 0.95 },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 6,
      })));
    return { nodes, edges };
  }, [tables, t]);

  if (failed) {
    return (
      <Card><CardContent className="space-y-3 py-16 text-center">
        <p className="text-sm text-destructive">{t('loadFailed')}</p>
        <Button variant="outline" size="sm" onClick={load}>{t('retry')}</Button>
      </CardContent></Card>
    );
  }
  if (!connected || !tables.length) {
    return (
      <Card><CardContent className="py-16 text-center text-sm text-muted-foreground">
        {connected ? t('noTables') : t('empty')}
      </CardContent></Card>
    );
  }

  return (
    <Card className="overflow-hidden p-0">
      <div style={{ height: 560 }} dir="ltr">
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView
          proOptions={{ hideAttribution: true }}>
          <Background gap={20} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </Card>
  );
}
