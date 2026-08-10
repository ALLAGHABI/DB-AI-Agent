'use client';
import {
  createColumnHelper, flexRender, getCoreRowModel, getSortedRowModel,
  useReactTable, type SortingState,
} from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { useFormatter, useTranslations } from 'next-intl';
import { useMemo, useState } from 'react';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';

type Row = Record<string, unknown>;

export function ResultsTable({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  const t = useTranslations('query');
  const format = useFormatter();
  const [sorting, setSorting] = useState<SortingState>([]);

  const data = useMemo<Row[]>(
    () => rows.map(r => Object.fromEntries(columns.map((c, i) => [c, r[i]]))),
    [columns, rows],
  );

  const helper = createColumnHelper<Row>();
  const cols = useMemo(
    () => columns.map(c =>
      helper.accessor(row => row[c], {
        id: c,
        header: ({ column }) => {
          const dir = column.getIsSorted();
          const Icon = dir === 'asc' ? ArrowUp : dir === 'desc' ? ArrowDown : ArrowUpDown;
          return (
            <button type="button" className="flex cursor-pointer items-center gap-1 font-mono text-xs font-semibold"
              onClick={() => column.toggleSorting(dir === 'asc')}>
              {c}<Icon className={`h-3 w-3 ${dir ? 'text-primary' : 'opacity-50'}`} />
            </button>
          );
        },
        cell: info => {
          const v = info.getValue();
          if (v === null || v === undefined) return <span className="text-muted-foreground">—</span>;
          if (typeof v === 'number') {
            return <span className="block text-end font-mono tabular-nums">{format.number(v)}</span>;
          }
          return <bdi>{String(v)}</bdi>;
        },
      })),
    [columns, helper, format],
  );

  const table = useReactTable({
    data, columns: cols, state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (!rows.length) return <div className="py-12 text-center text-sm text-muted-foreground">{t('noResults')}</div>;

  return (
    <div>
      <div className="max-h-[480px] overflow-auto rounded-lg border">
        <Table>
          <TableHeader className="sticky top-0 bg-card">
            {table.getHeaderGroups().map(hg => (
              <TableRow key={hg.id}>
                {hg.headers.map(h => (
                  <TableHead key={h.id}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map(row => (
              <TableRow key={row.id}>
                {row.getVisibleCells().map(cell => (
                  <TableCell key={cell.id} className="text-sm">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="pt-2 text-xs text-muted-foreground">{t('rowCount', { count: rows.length })}</div>
    </div>
  );
}
