interface Segment {
  type: "markdown" | "table";
  content: string;
  headers?: string[];
  rows?: string[][];
}

export function parseMarkdownTables(text: string): Segment[] {
  const segments: Segment[] = [];
  const lines = text.split("\n");
  let buffer: string[] = [];
  let tableLines: string[] = [];
  let inTable = false;

  const flushBuffer = () => {
    if (buffer.length > 0) {
      const content = buffer.join("\n").trim();
      if (content) segments.push({ type: "markdown", content });
      buffer = [];
    }
  };

  const flushTable = () => {
    if (tableLines.length < 2) {
      buffer.push(...tableLines);
      tableLines = [];
      inTable = false;
      return;
    }

    const parsed = parseTableLines(tableLines);
    if (parsed && parsed.headers.length >= 2) {
      flushBuffer();
      segments.push({ type: "table", content: "", headers: parsed.headers, rows: parsed.rows });
    } else {
      buffer.push(...tableLines);
    }
    tableLines = [];
    inTable = false;
  };

  for (const line of lines) {
    const trimmed = line.trim();
    const isSeparator = /^\|?[\s\-:]+(\|[\s\-:]+)+\|?$/.test(trimmed);
    const isTableRow = /^\|/.test(trimmed);

    if (isTableRow) {
      if (!inTable) {
        flushBuffer();
        inTable = true;
      }
      tableLines.push(line);
    } else if (inTable && isSeparator) {
      tableLines.push(line);
    } else {
      if (inTable) flushTable();
      buffer.push(line);
    }
  }

  if (inTable) flushTable();
  flushBuffer();

  return segments;
}

function parseTableLines(lines: string[]): { headers: string[]; rows: string[][] } | null {
  const separatorIdx = lines.findIndex((l) =>
    /^\|?[\s\-:]+(\|[\s\-:]+)+\|?$/.test(l.trim())
  );
  if (separatorIdx < 1) return null;

  const headers = parseRow(lines[0]);
  if (headers.length < 2) return null;

  const seen = new Set<string>();
  const uniqueHeaders = headers.map((h) => {
    const base = h || "col";
    let name = base;
    let counter = 1;
    while (seen.has(name)) {
      name = `${base}_${counter++}`;
    }
    seen.add(name);
    return name;
  });

  const dataLines = lines.slice(separatorIdx + 1).filter(
    (l) => l.trim().length > 0 && /^\|/.test(l.trim())
  );
  const rows = dataLines.map(parseRow);

  return { headers: uniqueHeaders, rows };
}

function parseRow(line: string): string[] {
  const parts = line.split("|");
  const result: string[] = [];
  for (let i = 1; i < parts.length - 1; i++) {
    result.push(parts[i].trim());
  }
  if (result.length === 0 && parts.length > 0) {
    return parts.map((p) => p.trim()).filter((p) => p.length > 0);
  }
  return result;
}
