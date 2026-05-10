import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { previewFile } from "../../api/client";
import type { FileInfo, FilePreview } from "../../types";

interface Props {
  file: FileInfo;
  onClose: () => void;
}

export function FilePreviewModal({ file, onClose }: Props) {
  const [data, setData] = useState<FilePreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    previewFile(file.file_id, 50)
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [file.file_id]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal modal-preview"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2>{file.table_name}</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading && <p className="preview-loading">Загрузка данных...</p>}
          {error && <p className="preview-error">Ошибка: {error}</p>}
          {data && (
            <div className="preview-info">
              <span className="preview-meta">
                {data.total_rows.toLocaleString()} строк &middot;{" "}
                {data.columns.length} колонок
              </span>
              {data.total_rows > 50 && (
                <span className="preview-note">
                  Показано первых 50 строк
                </span>
              )}
            </div>
          )}
          {data && (
            <div className="preview-table-wrap">
              <table className="preview-table">
                <thead>
                  <tr>
                    {data.columns.map((col, i) => (
                      <th key={i}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) => (
                        <td key={ci}>
                          {cell === null ? (
                            <span className="null-cell">NULL</span>
                          ) : (
                            String(cell)
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
