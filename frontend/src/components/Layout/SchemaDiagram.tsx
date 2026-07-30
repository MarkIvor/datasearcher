interface Props {
  files: { table_name: string; columns: { name: string; type: string }[]; row_count: number }[];
}

export function SchemaDiagram({ files }: Props) {
  if (files.length === 0) return null;

  return (
    <div className="er-schema">
      <div className="er-schema-title">Схема данных</div>
      <div className="er-tables">
        {files.map((f) => (
          <div key={f.table_name} className="er-table">
            <div className="er-table-header">
              {f.table_name}
              <span style={{ fontWeight: 400, opacity: 0.7, marginLeft: 6, fontSize: 9 }}>
                {f.row_count.toLocaleString()} строк
              </span>
            </div>
            <div className="er-table-cols">
              {f.columns.map((col, i) => (
                <div key={i} className="er-col">
                  <span className="er-col-name">{col.name}</span>
                  <span className="er-col-type">{col.type}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
