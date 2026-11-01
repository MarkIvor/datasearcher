import { useState, useRef, type DragEvent } from "react";
import { Upload, FileSpreadsheet, X, Loader2 } from "lucide-react";
import type { FileInfo } from "../../types";
import { useI18n } from "../../i18n";

interface Props {
  files: FileInfo[];
  uploading: boolean;
  onUpload: (file: File) => Promise<FileInfo | undefined>;
  onRemove: (fileId: string) => void;
}

export function FileUpload({ files, uploading, onUpload, onRemove }: Props) {
  const { t, fmt } = useI18n();
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) await onUpload(file);
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await onUpload(file);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="file-upload-panel">
      <h3>{t("files.title")}</h3>

      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? (
          <Loader2 className="spin" size={20} />
        ) : (
          <Upload size={20} />
        )}
        <span>{uploading ? t("files.uploading") : t("files.drop")}</span>
        <span className="hint">{t("files.hint")}</span>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={handleChange}
          hidden
        />
      </div>

      <div className="file-list">
        {files.map((f) => (
          <div key={f.file_id} className="file-item">
            <FileSpreadsheet size={14} />
            <div className="file-info">
              <span className="file-name">{f.table_name}</span>
              <span className="file-meta">
                {f.file_type.toUpperCase()} &middot; {t("files.rowsShort", { n: fmt(f.row_count) })}
              </span>
            </div>
            <button
              className="file-remove"
              onClick={() => onRemove(f.file_id)}
              title={t("common.delete")}
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
