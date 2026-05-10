import type { FileInfo } from "../../types";
import { Database, HardDrive, Clock } from "lucide-react";

interface Props {
  files: FileInfo[];
  lastQueryTime?: number;
}

export function StatusBar({ files, lastQueryTime }: Props) {
  const totalRows = files.reduce((sum, f) => sum + f.row_count, 0);
  const totalCols = files.reduce((sum, f) => sum + f.columns.length, 0);

  return (
    <div className="status-bar">
      <div className="status-item">
        <Database size={12} />
        <span>{files.length} таблиц</span>
      </div>
      <div className="status-item">
        <HardDrive size={12} />
        <span>{totalRows.toLocaleString()} строк</span>
      </div>
      <div className="status-item">
        <span>{totalCols} колонок</span>
      </div>
      {lastQueryTime !== undefined && (
        <div className="status-item">
          <Clock size={12} />
          <span>{lastQueryTime.toFixed(1)}s</span>
        </div>
      )}
    </div>
  );
}
