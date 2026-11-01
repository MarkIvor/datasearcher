import type { FileInfo } from "../../types";
import { Database, HardDrive, Clock } from "lucide-react";
import { useI18n } from "../../i18n";

interface Props {
  files: FileInfo[];
  lastQueryTime?: number;
}

export function StatusBar({ files, lastQueryTime }: Props) {
  const { t, fmt } = useI18n();
  const totalRows = files.reduce((sum, f) => sum + f.row_count, 0);
  const totalCols = files.reduce((sum, f) => sum + f.columns.length, 0);

  return (
    <div className="status-bar">
      <div className="status-item">
        <Database size={12} />
        <span>{t("status.tables", { n: files.length })}</span>
      </div>
      <div className="status-item">
        <HardDrive size={12} />
        <span>{t("status.rows", { n: fmt(totalRows) })}</span>
      </div>
      <div className="status-item">
        <span>{t("status.cols", { n: totalCols })}</span>
      </div>
      {lastQueryTime !== undefined && (
        <div className="status-item">
          <Clock size={12} />
          <span>{t("status.seconds", { n: lastQueryTime.toFixed(1) })}</span>
        </div>
      )}
    </div>
  );
}
