import React from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T, index: number) => React.ReactNode;
  className?: string;
  headerClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T, index: number) => string;
  emptyMessage?: string;
  isLoading?: boolean;
  className?: string;
  onRowClick?: (item: T) => void;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = 'No data available',
  isLoading = false,
  className = '',
  onRowClick,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="w-full bg-card rounded-xl border border-border p-8 flex justify-center items-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue" />
        <span className="ml-3 text-sm text-muted">Loading table records...</span>
      </div>
    );
  }

  return (
    <div className={`w-full bg-card rounded-xl border border-border shadow-sm overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-text">
          <thead className="bg-bg/70 text-xs font-semibold text-muted uppercase tracking-wider border-b border-border">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-5 py-3.5 ${col.headerClassName || ''} ${col.className || ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-5 py-8 text-center text-sm text-muted"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item, index) => (
                <tr
                  key={keyExtractor(item, index)}
                  onClick={() => onRowClick?.(item)}
                  className={`transition-colors hover:bg-bg/50 ${
                    onRowClick ? 'cursor-pointer' : ''
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-5 py-3.5 whitespace-nowrap text-sm text-text ${
                        col.className || ''
                      }`}
                    >
                      {col.render
                        ? col.render(item, index)
                        : (item as Record<string, unknown>)[col.key] !== undefined
                        ? String((item as Record<string, unknown>)[col.key])
                        : '—'}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
