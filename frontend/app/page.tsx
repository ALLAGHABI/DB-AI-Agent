'use client';
import { useCallback, useState } from 'react';
import { ConnectionsPanel } from '@/components/connections-panel';
import { ProvidersPanel, type ModelSelection } from '@/components/providers-panel';
import { QueryWorkspace } from '@/components/query-workspace';
import { Shell } from '@/components/shell';

export default function Home() {
  const [tables, setTables] = useState<string[]>([]);
  const [selection, setSelection] = useState<ModelSelection | null>(null);
  const onConnected = useCallback((t: string[]) => setTables(t), []);
  const onModelChange = useCallback((s: ModelSelection | null) => setSelection(s), []);

  return (
    <Shell connected={tables.length > 0}
      sidebar={<>
        <ConnectionsPanel onConnected={onConnected} />
        <ProvidersPanel onModelChange={onModelChange} />
      </>}
      main={<QueryWorkspace connected={tables.length > 0} selection={selection} />}
    />
  );
}
