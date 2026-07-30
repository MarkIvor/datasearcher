import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, ArrowUp, ArrowDown, Search, ChevronLeft, ChevronRight, Download } from "lucide-react";
import Markdown from "react-markdown";

function InlineMd({ text }: { text: string }) {
  return <Markdown components={{ p: "span", code: "code", em: "em", strong: "strong", del: "del" }}>{text}</Markdown>;
}

interface Props {
  headers: string[];
  rows: string[][];
  title?: string;
}

export function InteractiveTable({ headers, rows, title }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const safeHeaders = useMemo(
    () => headers.map((h, i) => h || `col_${i}`),
    [headers]
  );

  const data = useMemo(
    () =>
      rows.map((row, i) => {
        const obj: Record<string, string> = { _idx: String(i + 1) };
        safeHeaders.forEach((h, j) => {
          obj[h] = row[j] ?? "";
        });
        return obj;
      }),
    [safeHeaders, rows]
  );

  const columns = useMemo<ColumnDef<Record<string, string>>[]>(
    () => [
      {
        id: "_idx",
        header: "#",
        accessorKey: "_idx",
        size: 40,
        enableSorting: false,
      },
      ...safeHeaders.map((h, i) => ({
        id: `col_${i}_${h}`,
        header: h,
        accessorKey: h,
        size: undefined as number | undefined,
        cell: (info: { getValue: () => unknown }) => {
          const v = String(info.getValue());
          const isNum = v !== "" && !isNaN(Number(v));
          return (
            <span className={isNum ? "cell-num" : ""}>
              {v === "None" || v === "null" || v === "NULL" ? (
                <span className="null-cell">NULL</span>
              ) : isNum ? (
                v
              ) : (
                <InlineMd text={v} />
              )}
            </span>
          );
        },
      })),
    ],
    [safeHeaders]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 15 } },
  });

  const handleCopyCSV = () => {
    const csvRows = [safeHeaders.join(",")];
    for (const row of rows) {
      csvRows.push(row.map((c) => `"${c.replace(/"/g, '""')}"`).join(","));
    }
    navigator.clipboard.writeText(csvRows.join("\n"));
  };

  return (
    <div className="itable">
      <div className="itable-header">
        {title && <span className="itable-title">{title}</span>}
        <span className="itable-count">
          {rows.length} строк &times; {safeHeaders.length} колонок
        </span>
        <div className="itable-controls">
          <div className="itable-search">
            <Search size={13} />
            <input
              type="text"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder="Поиск..."
            />
          </div>
          <button className="itable-btn" onClick={handleCopyCSV} title="Копировать CSV">
            <Download size={13} />
          </button>
        </div>
      </div>
      <div className="itable-wrap">
        <table className="itable-table">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    style={{ width: header.getSize() !== 150 ? header.getSize() : undefined, cursor: header.column.getCanSort() ? "pointer" : "default" }}
                  >
                    <span className="th-content">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <span className="th-sort">
                          {header.column.getIsSorted() === "asc" ? (
                            <ArrowUp size={12} />
                          ) : header.column.getIsSorted() === "desc" ? (
                            <ArrowDown size={12} />
                          ) : (
                            <ArrowUpDown size={12} opacity={0.3} />
                          )}
                        </span>
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td colSpan={safeHeaders.length + 1} className="itable-empty">
                  Ничего не найдено
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="itable-footer">
        <button
          className="itable-page-btn"
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
        >
          <ChevronLeft size={14} />
        </button>
        <span className="itable-page-info">
          {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
        </span>
        <button
          className="itable-page-btn"
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
