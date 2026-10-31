from __future__ import annotations

import csv
import json
import os
import secrets
import tempfile

from ..session import Session
from .registry import register_tool


def _generate_slug() -> str:
    return secrets.token_urlsafe(6)[:8]


def _safe_val(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        import math

        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    try:
        if hasattr(v, "item"):
            return v.item()
    except Exception:
        pass
    return str(v)


def _create_snapshot(session: Session, dash_dir: str) -> tuple[str, list[dict]]:
    slug = _generate_slug()
    snap_dir = os.path.join(dash_dir, slug)
    os.makedirs(snap_dir, exist_ok=True)

    tables_info: list[dict] = []
    for fi in session.files.values():
        csv_path = os.path.join(snap_dir, f"{fi.table_name}.csv")
        try:
            result = session.conn.execute(f'SELECT * FROM "{fi.table_name}"')
            columns = [d[0] for d in result.description]
            rows = result.fetchall()
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([str(v) if v is not None else "" for v in row])

            desc = session.conn.execute(f'DESCRIBE "{fi.table_name}"').fetchall()
            actual_types = {r[0]: r[1] for r in desc}
            enriched_columns = [
                {"name": col["name"], "type": actual_types.get(col["name"], col.get("type", "unknown"))}
                for col in fi.columns
            ]
            tables_info.append(
                {"name": fi.table_name, "row_count": len(rows), "columns": enriched_columns}
            )
        except Exception:
            pass
    return snap_dir, tables_info


def _get_unique_counts(session: Session, tables_info: list[dict]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for t in tables_info:
        tname = t["name"]
        col_counts: dict[str, int] = {}
        for col in t.get("columns", []):
            cname = col["name"]
            try:
                row = session.conn.execute(
                    f'SELECT COUNT(DISTINCT "{cname}") FROM "{tname}"'
                ).fetchone()
                col_counts[cname] = row[0] if row else 0
            except Exception:
                col_counts[cname] = 999
        result[tname] = col_counts
    return result


def _generate_config(session: Session, tables_info: list[dict], title: str, description: str) -> dict:
    selectors: list[dict] = []
    cards: list[dict] = []

    def is_text(t: str) -> bool:
        t = t.lower()
        return any(x in t for x in ("varchar", "text", "string", "char", "enum", "blob"))

    def is_num(t: str) -> bool:
        t = t.lower()
        return any(x in t for x in ("int", "float", "double", "decimal", "numeric", "real", "hugeint"))

    def is_date(t: str) -> bool:
        t = t.lower()
        return any(x in t for x in ("date", "timestamp", "datetime", "time"))

    unique_counts = _get_unique_counts(session, tables_info)
    CATEGORY_THRESHOLD = 20

    for t in tables_info:
        tname = t["name"]
        text_cols: list[str] = []
        num_cols: list[str] = []
        date_cols: list[str] = []
        low_card_numeric: list[str] = []

        for col in t.get("columns", []):
            cname = col["name"]
            ctype = col.get("type", "")
            ucount = unique_counts.get(tname, {}).get(cname, 999)

            if is_text(ctype):
                text_cols.append(cname)
                if len(selectors) < 6 and ucount > 1:
                    selectors.append({"id": f"{tname}_{cname}", "type": "category", "column": cname, "table": tname, "label": cname})
            elif is_num(ctype):
                if ucount <= CATEGORY_THRESHOLD and ucount > 1 and ucount < t.get("row_count", 0) * 0.8:
                    low_card_numeric.append(cname)
                    if len(selectors) < 6:
                        selectors.append({"id": f"{tname}_{cname}", "type": "category", "column": cname, "table": tname, "label": cname})
                else:
                    num_cols.append(cname)
                    if len(selectors) < 6:
                        selectors.append({"id": f"{tname}_{cname}_range", "type": "number_range", "column": cname, "table": tname, "label": f"{cname} (диапазон)"})
            elif is_date(ctype):
                date_cols.append(cname)
                if len(selectors) < 6:
                    selectors.append({"id": f"{tname}_{cname}_date", "type": "date_range", "column": cname, "table": tname, "label": f"{cname} (период)"})

        all_category_cols = text_cols + low_card_numeric

        if t.get("row_count", 0) > 0:
            cards.append({
                "id": f"count_{tname}",
                "type": "kpi",
                "title": f"Всего записей ({tname})",
                "query": f'SELECT COUNT(*) AS value FROM "{tname}" {{WHERE}}',
                "format": "number",
            })

            num_cols_for_cards = [nc for nc in num_cols if unique_counts.get(tname, {}).get(nc, 999) < t.get("row_count", 0) * 0.8]
            for nc in num_cols_for_cards[:2]:
                if len(cards) < 12:
                    cards.append({
                        "id": f"avg_{tname}_{nc}",
                        "type": "kpi",
                        "title": f"Средний {nc}",
                        "query": f'SELECT AVG("{nc}") AS value FROM "{tname}" {{WHERE}}',
                        "format": "number",
                    })

            for cc in all_category_cols[:3]:
                if len(cards) < 12 and num_cols_for_cards:
                    nc = num_cols_for_cards[0]
                    cards.append({
                        "id": f"avg_{tname}_{cc}_{nc}",
                        "type": "chart",
                        "title": f"Средний {nc} по {cc}",
                        "query": f'SELECT "{cc}", AVG("{nc}") AS avg_val FROM "{tname}" {{WHERE}} GROUP BY "{cc}" ORDER BY avg_val DESC LIMIT 12',
                        "chart_type": "bar",
                        "x": cc,
                        "y": "avg_val",
                    })
                if len(cards) < 12:
                    cards.append({
                        "id": f"dist_{tname}_{cc}",
                        "type": "chart",
                        "title": f"Распределение {cc}",
                        "query": f'SELECT "{cc}", COUNT(*) AS cnt FROM "{tname}" {{WHERE}} GROUP BY "{cc}" ORDER BY cnt DESC LIMIT 10',
                        "chart_type": "pie",
                        "x": cc,
                        "y": "cnt",
                    })

            if len(num_cols_for_cards) >= 2 and len(cards) < 12:
                x_col, y_col = num_cols_for_cards[0], num_cols_for_cards[1]
                cards.append({
                    "id": f"scatter_{tname}",
                    "type": "chart",
                    "title": f"{x_col} vs {y_col}",
                    "query": f'SELECT "{x_col}", "{y_col}" FROM "{tname}" {{WHERE}} LIMIT 200',
                    "chart_type": "scatter",
                    "x": x_col,
                    "y": y_col,
                })

            if date_cols and num_cols_for_cards and len(cards) < 12:
                dc = date_cols[0]
                nc = num_cols_for_cards[0]
                cards.append({
                    "id": f"trend_{tname}_{nc}",
                    "type": "chart",
                    "title": f"Тренд {nc}",
                    "query": f"SELECT DATE_TRUNC('month', \"{dc}\") AS period, AVG(\"{nc}\") AS val FROM \"{tname}\" {{WHERE}} GROUP BY period ORDER BY period",
                    "chart_type": "line",
                    "x": "period",
                    "y": "val",
                })

    return {"title": title, "description": description, "selectors": selectors, "cards": cards}


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/duckdb@1.0.0/dist/duckdb.wasm.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background:#f5f6f8; color:#1f2330; }}
header {{ background: linear-gradient(135deg,#4f46e5,#7c3aed); color:#fff; padding: 24px 32px; }}
header h1 {{ margin: 0 0 4px; font-size: 24px; }}
header p {{ margin: 0; opacity: .85; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 12px; padding: 16px 32px; background:#fff; border-bottom:1px solid #e5e7eb; }}
.control {{ display:flex; flex-direction:column; gap:4px; min-width:160px; }}
.control label {{ font-size: 12px; font-weight:600; color:#6b7280; }}
select, input {{ padding:6px 8px; border:1px solid #d1d5db; border-radius:6px; font-size:13px; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap:16px; padding:24px 32px; }}
.card {{ background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
.card h3 {{ margin:0 0 8px; font-size:14px; color:#374151; }}
.kpi {{ font-size: 28px; font-weight:700; color:#4f46e5; }}
.chart-box {{ height: 240px; }}
.loading {{ color:#9ca3af; font-size:13px; }}
</style>
</head>
<body>
<header><h1>{title}</h1><p>{description}</p></header>
<div class="controls" id="controls"></div>
<div class="grid" id="grid"></div>
<script>
const CONFIG = {config};
const TABLES = {tables_json};
const CSV_DATA = {csv_json};

let db;
async function initDB() {{
  duckdb.boot().then(async () => {{
    const conn = await duckdb.connect();
    for (const t of TABLES) {{
      const csv = CSV_DATA[t.name];
      await conn.query(`CREATE TABLE "${{t.name}}" AS SELECT * FROM read_csv_auto('${{csv}}', header=true)`);
    }}
    db = conn;
    buildControls();
    await renderAll();
  }}).catch(e => {{
    document.getElementById('grid').innerHTML = '<div class="card">Ошибка DuckDB-WASM: '+e.message+'<br>Дашборд требует интернет для загрузки duckdb-wasm.</div>';
  }});
}}

function buildControls() {{
  const wrap = document.getElementById('controls');
  CONFIG.selectors.forEach(sel => {{
    const div = document.createElement('div');
    div.className = 'control';
    div.innerHTML = `<label>${{sel.label}}</label>`;
    let input;
    if (sel.type === 'category') {{
      input = document.createElement('select');
      const opt = document.createElement('option'); opt.value=''; opt.textContent='Все'; input.appendChild(opt);
      input.addEventListener('change', renderAll);
    }} else if (sel.type === 'number_range') {{
      input = document.createElement('input'); input.type='text'; input.placeholder='min-max';
      input.addEventListener('input', renderAll);
    }} else if (sel.type === 'date_range') {{
      input = document.createElement('input'); input.type='text'; input.placeholder='YYYY-MM-DD - YYYY-MM-DD';
      input.addEventListener('input', renderAll);
    }}
    input.dataset.id = sel.id;
    div.appendChild(input);
    wrap.appendChild(div);
    if (sel.type === 'category') loadCategories(sel, input);
  }});
}}

async function loadCategories(sel, input) {{
  try {{
    const res = await db.query(`SELECT DISTINCT "${{sel.column}}" AS v FROM "${{sel.table}}" WHERE "${{sel.column}}" IS NOT NULL ORDER BY v LIMIT 50`);
    const rows = res.toArray ? res.toArray() : [];
    rows.forEach(r => {{ const v = r.v ?? r[0]; const o=document.createElement('option'); o.value=v; o.textContent=v; input.appendChild(o); }});
  }} catch(e) {{}}
}}

function buildWhere() {{
  const conds = [];
  document.querySelectorAll('.control [data-id]').forEach(el => {{
    const sel = CONFIG.selectors.find(s => s.id === el.dataset.id);
    if (!sel) return;
    const val = el.value.trim();
    if (!val) return;
    if (sel.type === 'category') {{
      const v = String(val).replace(/'/g, "''");
      conds.push(`"${{sel.column}}"='${{v}}'`);
    }} else if (sel.type === 'number_range') {{
      const [mn, mx] = val.split('-').map(s => s.trim());
      if (mn) conds.push(`"${{sel.column}}" >= ${{mn}}`);
      if (mx) conds.push(`"${{sel.column}}" <= ${{mx}}`);
    }} else if (sel.type === 'date_range') {{
      const [d0, d1] = val.split('-').map(s => s.trim());
      if (d0) conds.push(`"${{sel.column}}" >= '${{d0}}'`);
      if (d1) conds.push(`"${{sel.column}}" <= '${{d1}}'`);
    }}
  }});
  return conds.length ? 'WHERE ' + conds.join(' AND ') : '';
}}

const chartInstances = {{}};
async function renderAll() {{
  const where = buildWhere();
  const grid = document.getElementById('grid');
  CONFIG.cards.forEach(async card => {{
    let el = document.getElementById(card.id);
    if (!el) {{
      el = document.createElement('div'); el.className='card'; el.id=card.id;
      el.innerHTML = card.type==='kpi'
        ? `<h3>${{card.title}}</h3><div class="kpi" data-val></div>`
        : `<h3>${{card.title}}</h3><div class="chart-box"><canvas></canvas></div>`;
      grid.appendChild(el);
    }}
    try {{
      const sql = card.query.replace('{{WHERE}}', where);
      const res = await db.query(sql);
      const rows = res.toArray ? res.toArray() : [];
      if (card.type === 'kpi') {{
        el.querySelector('[data-val]').textContent = rows[0] ? Number(rows[0].value ?? rows[0][0]).toLocaleString('ru-RU') : '—';
      }} else {{
        const labels = rows.map(r => String(r[card.x] ?? Object.values(r)[0]));
        const data = rows.map(r => Number(r[card.y] ?? Object.values(r)[1]));
        if (chartInstances[card.id]) chartInstances[card.id].destroy();
        chartInstances[card.id] = new Chart(el.querySelector('canvas'), {{
          type: card.chart_type === 'scatter' ? 'scatter' : card.chart_type,
          data: {{ labels: card.chart_type==='scatter' ? undefined : labels, datasets: [{{ label: card.title, data: card.chart_type==='scatter' ? rows.map(r=>({{x:+r[card.x],y:+r[card.y]}})) : data, backgroundColor: ['#4f46e5','#7c3aed','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316'] }}] }},
          options: {{ responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display: card.chart_type==='pie'}}}} }}
        }});
      }}
    }} catch(e) {{ if (el) el.innerHTML = `<h3>${{card.title}}</h3><div class="loading">Ошибка: ${{e.message}}</div>`; }}
  }});
}}
initDB();
</script>
</body>
</html>
"""


def _build_html(config: dict, tables_info: list[dict], snap_dir: str) -> str:
    csv_map = {}
    for t in tables_info:
        rel = f"{t['name']}.csv"
        csv_map[t["name"]] = rel
    return _HTML_TEMPLATE.format(
        title=config["title"],
        description=config.get("description", ""),
        config=json.dumps(config, ensure_ascii=False, default=str),
        tables_json=json.dumps(tables_info, ensure_ascii=False, default=str),
        csv_json=json.dumps(csv_map, ensure_ascii=False, default=str),
    )


@register_tool(
    name="create_public_dashboard",
    description=(
        "Создаёт дашборд — standalone HTML-страницу с интерактивными фильтрами "
        "(селекторы категорий, диапазоны дат и чисел), KPI-карточками, графиками и "
        "таблицами. Данные и конфигурация встраиваются в файл; интерактивность "
        "обеспечивается DuckDB-WASM и Chart.js (требуется интернет для загрузки libs). "
        "Возвращает путь к HTML-файлу. ВЫЗЫВАЙ когда пользователь просит 'создай дашборд', "
        "'опубликуй дашборд', 'сделай дашборд'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Название дашборда"},
            "description": {"type": "string", "description": "Краткое описание дашборда"},
        },
        "required": ["title"],
    },
)
def create_public_dashboard(session: Session, title: str, description: str = "") -> str:
    if not session.files:
        return "Ошибка: нет загруженных данных. Загрузите таблицы/подключите БД перед созданием дашборда."

    from ..config import settings

    dash_dir = settings.dashboards_dir or os.path.join(
        tempfile.gettempdir(), "datasearcher_mcp_dashboards"
    )
    os.makedirs(dash_dir, exist_ok=True)
    snap_dir, tables_info = _create_snapshot(session, dash_dir)
    if not tables_info:
        return "Ошибка: не удалось создать снапшот данных."

    slug = _generate_slug()
    config = _generate_config(session, tables_info, title, description)
    html = _build_html(config, tables_info, snap_dir)

    html_path = os.path.join(snap_dir, "dashboard.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return (
        f"__DASHBOARD_CREATED__\n"
        f"{json.dumps({'slug': slug, 'title': title, 'path': html_path, 'cards': len(config['cards']), 'selectors': len(config['selectors'])}, ensure_ascii=False)}\n"
        f"__END_DASHBOARD_CREATED__"
    )
