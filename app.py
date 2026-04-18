import base64
import html
import json
import os
import sqlite3
import sys
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request
from urllib.parse import parse_qs, quote, urlparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "rds_registry.sqlite3")
HOST = "127.0.0.1"
PORT = 8000
STATUSES = (
    "registrerad",
    "skickad_for_godkannande",
    "godkand",
    "ur_bruk",
)
LEVEL_LABELS = {
    1: "Driftområde",
    2: "Disciplin",
    3: "Funktions-ID för anläggning",
    4: "Funktionsklass",
    5: "Processenhet",
    6: "Utrustningsenhet",
    7: "Kontrollenhet",
}
CORE_LEVELS = (1, 2, 3, 4)
DETAIL_LEVELS = (5, 6, 7)


STYLE = """
<style>
  :root {
    --bg: #f4f1e8;
    --panel: #fffdf7;
    --ink: #1d2a30;
    --muted: #63727a;
    --line: #d7d0c2;
    --brand: #125f63;
    --brand-2: #d57f3a;
    --ok: #256f3a;
    --warn: #9a5c00;
    --bad: #9f2d22;
    --shadow: 0 14px 34px rgba(22, 35, 41, 0.08);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: "Segoe UI", sans-serif;
    background:
      radial-gradient(circle at top left, rgba(213, 127, 58, 0.12), transparent 30%),
      linear-gradient(180deg, #f8f5ee 0%, var(--bg) 100%);
    color: var(--ink);
  }
  a { color: var(--brand); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .shell { width: min(1200px, calc(100% - 32px)); margin: 24px auto 48px; }
  .hero {
    background: linear-gradient(135deg, rgba(18, 95, 99, 0.96), rgba(16, 49, 66, 0.98));
    color: white;
    padding: 28px;
    border-radius: 24px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
  }
  .hero h1 { margin: 0 0 8px; font-size: clamp(1.8rem, 3vw, 2.5rem); }
  .hero p { margin: 0; max-width: 780px; line-height: 1.5; color: rgba(255,255,255,0.86); }
  nav { display: flex; gap: 10px; flex-wrap: wrap; margin: 18px 0 22px; }
  nav a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 40px;
    padding: 10px 14px;
    border-radius: 999px;
    border: 1px solid rgba(18, 95, 99, 0.16);
    background: rgba(255,255,255,0.72);
    color: var(--ink);
  }
  nav a.active { background: var(--brand); color: white; border-color: var(--brand); }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
  .card, .table-wrap, form, .notice {
    background: var(--panel);
    border: 1px solid rgba(29, 42, 48, 0.08);
    border-radius: 20px;
    box-shadow: var(--shadow);
  }
  .card { padding: 18px; }
  .card h2, .table-wrap h2, form h2, .notice h2 {
    margin-top: 0;
    margin-bottom: 10px;
    font-size: 1.1rem;
  }
  .stat { font-size: 2rem; font-weight: 700; margin-bottom: 6px; }
  .muted { color: var(--muted); }
  .stack { display: grid; gap: 16px; }
  .table-wrap { overflow: hidden; }
  .table-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 18px 20px 0;
  }
  table { width: 100%; border-collapse: collapse; background: transparent; }
  th, td {
    padding: 12px 20px;
    border-bottom: 1px solid var(--line);
    text-align: left;
    vertical-align: top;
    font-size: 0.95rem;
  }
  th {
    color: var(--muted);
    font-weight: 600;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  tr:last-child td { border-bottom: 0; }
  form { padding: 20px; display: grid; gap: 16px; }
  .form-grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
  label { display: grid; gap: 6px; font-weight: 600; }
  input, select, textarea, button { font: inherit; }
  input, select, textarea {
    width: 100%;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid #c5ccc5;
    background: #fff;
    color: var(--ink);
  }
  textarea { min-height: 110px; resize: vertical; }
  .inline-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  button, .button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 42px;
    padding: 10px 16px;
    border-radius: 12px;
    border: 1px solid transparent;
    background: var(--brand);
    color: white;
    cursor: pointer;
    text-decoration: none;
  }
  .button.secondary, button.secondary {
    background: white;
    color: var(--ink);
    border-color: var(--line);
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: rgba(29, 42, 48, 0.08);
  }
  .status-registrerad { color: var(--warn); background: rgba(154, 92, 0, 0.12); }
  .status-skickad_for_godkannande { color: #1d4f91; background: rgba(29, 79, 145, 0.12); }
  .status-godkand { color: var(--ok); background: rgba(37, 111, 58, 0.12); }
  .status-ur_bruk { color: var(--bad); background: rgba(159, 45, 34, 0.12); }
  .flash {
    padding: 14px 16px;
    border-left: 4px solid var(--brand-2);
    background: rgba(213, 127, 58, 0.12);
    border-radius: 14px;
  }
  .soft-note {
    padding: 16px 18px;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(18, 95, 99, 0.08), rgba(18, 95, 99, 0.03));
    border: 1px solid rgba(18, 95, 99, 0.12);
  }
  .soft-note strong { display: block; margin-bottom: 6px; }
  .token-line {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  .token {
    display: inline-flex;
    align-items: center;
    min-height: 32px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(29, 42, 48, 0.06);
    border: 1px solid rgba(29, 42, 48, 0.08);
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.9rem;
  }
  .two-col { display: grid; gap: 16px; grid-template-columns: 1.2fr 0.8fr; }
  .mono { font-family: Consolas, "Courier New", monospace; font-size: 0.95rem; }
  .empty { padding: 28px 20px; color: var(--muted); }
  .meta-list { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
  .meta-list strong {
    display: block;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    margin-bottom: 4px;
  }
  .form-section {
    padding: 18px;
    border: 1px solid rgba(29, 42, 48, 0.08);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.55);
  }
  .form-section h3 {
    margin: 0 0 6px;
    font-size: 1rem;
  }
  .form-section p {
    margin: 0 0 14px;
    color: var(--muted);
  }
  details.form-section {
    padding: 0;
    overflow: hidden;
  }
  details.form-section summary {
    list-style: none;
    cursor: pointer;
    padding: 18px;
    font-weight: 700;
  }
  details.form-section summary::-webkit-details-marker { display: none; }
  details.form-section[open] summary {
    border-bottom: 1px solid var(--line);
    background: rgba(18, 95, 99, 0.04);
  }
  .details-body { padding: 18px; }
  .eyebrow {
    display: inline-block;
    margin-bottom: 10px;
    color: var(--brand);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.76rem;
  }
  @media (max-width: 900px) {
    .two-col { grid-template-columns: 1fr; }
    th:nth-child(4), td:nth-child(4),
    th:nth-child(5), td:nth-child(5) { display: none; }
  }
</style>
"""


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def get_connection():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(conn, table_name, column_name, definition):
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                designation TEXT NOT NULL UNIQUE,
                parent_object_id INTEGER,
                level1 TEXT,
                level2 TEXT,
                level3 TEXT,
                level4 TEXT,
                level5 TEXT,
                level6 TEXT,
                level7 TEXT,
                rds_code TEXT,
                title TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(parent_object_id) REFERENCES objects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS object_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER NOT NULL,
                version_no INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('registrerad','skickad_for_godkannande','godkand','ur_bruk')),
                valid_from TEXT,
                valid_to TEXT,
                source_drawing TEXT,
                drawing_revision TEXT,
                change_summary TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT,
                changed_at TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                FOREIGN KEY(object_id) REFERENCES objects(id) ON DELETE CASCADE,
                UNIQUE(object_id, version_no)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id INTEGER,
                version_id INTEGER,
                event_type TEXT NOT NULL,
                actor TEXT,
                details TEXT,
                event_time TEXT NOT NULL,
                FOREIGN KEY(object_id) REFERENCES objects(id) ON DELETE CASCADE,
                FOREIGN KEY(version_id) REFERENCES object_versions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_objects_levels
            ON objects(level1, level2, level3, level4, level5, level6, level7);

            CREATE INDEX IF NOT EXISTS idx_versions_status
            ON object_versions(status, valid_from, valid_to);
            """
        )
        ensure_column(conn, "object_versions", "jira_issue_key", "TEXT")
        ensure_column(conn, "object_versions", "jira_decision", "TEXT")
        ensure_column(conn, "object_versions", "jira_synced_at", "TEXT")
        ensure_column(conn, "object_versions", "jira_sync_status", "TEXT")
        ensure_column(conn, "objects", "parent_object_id", "INTEGER")
        rows = conn.execute(
            """
            SELECT id, level1, level2, level3, level4, level5, level6, level7, designation
            FROM objects
            """
        ).fetchall()
        for row in rows:
            generated = build_designation(row)
            if generated and row["designation"] != generated:
                conn.execute(
                    "UPDATE objects SET designation = ? WHERE id = ?",
                    (generated, row["id"]),
                )
        conn.commit()


def record_event(conn, object_id, version_id, event_type, actor, details):
    conn.execute(
        """
        INSERT INTO audit_log(object_id, version_id, event_type, actor, details, event_time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (object_id, version_id, event_type, actor, details, now_iso()),
    )


def esc(value):
    return html.escape("" if value is None else str(value))


def date_input_value(value):
    if not value:
        return ""
    return value[:10]


def fmt_datetime(value):
    if not value:
        return "Ej satt"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def fmt_date(value):
    if not value:
        return "Ej satt"
    return value[:10]


def level_label(index):
    return LEVEL_LABELS.get(index, f"Nivå {index}")


def level_value(row, index):
    return (row.get(f"level{index}") if isinstance(row, dict) else row[f"level{index}"]) or ""


def joined_levels(row, levels, empty_text="Ej satt"):
    values = [level_value(row, index) for index in levels if level_value(row, index)]
    return " / ".join(values) if values else empty_text


def has_detail_levels(row):
    return any(level_value(row, index) for index in DETAIL_LEVELS)


def object_scope_label(row):
    if level_value(row, 7):
        return "Kontrollenhet"
    if level_value(row, 6):
        return "Utrustningsenhet"
    if level_value(row, 5):
        return "Processenhet"
    return "Funktionsklass / huvudpost"


def is_main_object(row):
    return not has_detail_levels(row)


def detail_focus_label(child_kind):
    mapping = {
        "level5": "Processenhet",
        "level6": "Utrustningsenhet",
        "level7": "Kontrollenhet",
    }
    return mapping.get(child_kind, "Detaljnivå")


def latest_used_level(row):
    for index in (7, 6, 5, 4):
        if level_value(row, index):
            return index
    return 4


def build_designation(data):
    parts = []
    for index in range(1, 8):
        key = f"level{index}"
        if isinstance(data, dict):
            value = data.get(key, "")
        else:
            value = data[key]
        parts.append((value or "").strip())
    parts = [part for part in parts if part]
    return "=" + ".".join(parts) if parts else ""

def jira_config():
    return {
        "base_url": os.getenv("JIRA_BASE_URL", "").rstrip("/"),
        "email": os.getenv("JIRA_EMAIL", ""),
        "api_token": os.getenv("JIRA_API_TOKEN", ""),
        "bearer_token": os.getenv("JIRA_BEARER_TOKEN", ""),
        "decision_field": os.getenv("JIRA_DECISION_FIELD", ""),
    }


def jira_ready(config=None):
    config = config or jira_config()
    has_auth = bool((config["email"] and config["api_token"]) or config["bearer_token"])
    return bool(config["base_url"] and config["decision_field"] and has_auth)


def jira_headers(config):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if config["bearer_token"]:
        headers["Authorization"] = f"Bearer {config['bearer_token']}"
    else:
        token = f"{config['email']}:{config['api_token']}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(token).decode("ascii")
    return headers


def jira_request_json(path, config):
    req = request.Request(
        config["base_url"] + path,
        headers=jira_headers(config),
        method="GET",
    )
    with request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_jira_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("value", "name", "displayName"):
            if value.get(key):
                return str(value[key])
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return ", ".join(part for part in (normalize_jira_value(item) for item in value) if part)
    return str(value)


def resolve_decision_field_id(config):
    field_name = config["decision_field"]
    if field_name.startswith("customfield_"):
        return field_name
    payload = jira_request_json("/rest/api/3/field", config)
    for field in payload:
        if str(field.get("id", "")).startswith("customfield_") and field.get("name", "").strip().lower() == field_name.strip().lower():
            return field["id"]
    raise ValueError(f"Kunde inte hitta Jira-fältet '{field_name}'. Ange gärna customfield_xxxxx direkt.")


def fetch_jira_issue(issue_key):
    config = jira_config()
    if not jira_ready(config):
        raise ValueError("Jira är inte färdigkonfigurerat. Sätt JIRA_BASE_URL, auth och JIRA_DECISION_FIELD.")
    field_id = resolve_decision_field_id(config)
    fields = f"summary,status,{field_id}"
    payload = jira_request_json(f"/rest/api/3/issue/{issue_key}?fields={fields}", config)
    fields_data = payload.get("fields", {})
    decision = normalize_jira_value(fields_data.get(field_id))
    status_name = normalize_jira_value(fields_data.get("status"))
    return {
        "issue_key": payload.get("key", issue_key),
        "decision": decision,
        "status": status_name,
        "synced_at": now_iso(),
    }


def sync_version_from_jira(conn, version_id):
    row = conn.execute(
        "SELECT id, object_id, jira_issue_key FROM object_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    if not row or not (row["jira_issue_key"] or "").strip():
        raise ValueError("Ingen Jira-nyckel finns angiven för versionen.")
    try:
        issue = fetch_jira_issue(row["jira_issue_key"].strip())
        conn.execute(
            """
            UPDATE object_versions
            SET jira_issue_key = ?, jira_decision = ?, jira_synced_at = ?, jira_sync_status = ?
            WHERE id = ?
            """,
            (
                issue["issue_key"],
                issue["decision"],
                issue["synced_at"],
                issue["status"],
                version_id,
            ),
        )
        record_event(
            conn,
            row["object_id"],
            version_id,
            "jira_sync",
            "Jira API",
            f"Beslut hämtades från Jira-ärende {issue['issue_key']}.",
        )
        conn.commit()
        return issue
    except error.HTTPError as exc:
        raise ValueError(f"Jira svarade med HTTP {exc.code}.")
    except error.URLError:
        raise ValueError("Kunde inte nå Jira från appen.")


def build_page(title, body, active="", flash=""):
    nav_items = [
        ("/", "Översikt", ""),
        ("/objects", "Register", "objects"),
        ("/objects/new", "Ny registrering", "new"),
        ("/checks", "Krockkontroll", "checks"),
        ("/export.csv", "Export CSV", ""),
    ]
    nav_html = "".join(
        f'<a class="{"active" if key == active else ""}" href="{href}">{label}</a>'
        for href, label, key in nav_items
    )
    flash_html = f'<div class="flash">{esc(flash)}</div>' if flash else ""
    return f"""<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  {STYLE}
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Referensbeteckningsregister</h1>
      <p>Lokalt register för manuell registrering från ritningar, versionshistorik, giltighet och kontroll av potentiella dubletter.</p>
    </section>
    <nav>{nav_html}</nav>
    <div class="stack">
      {flash_html}
      {body}
    </div>
  </div>
</body>
</html>"""


def redirect(handler, location):
    handler.send_response(HTTPStatus.SEE_OTHER)
    handler.send_header("Location", location)
    handler.end_headers()


def parse_post_data(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length).decode("utf-8")
    parsed = parse_qs(raw, keep_blank_values=True)
    return {key: values[0].strip() for key, values in parsed.items()}


def get_query_params(handler):
    parsed = urlparse(handler.path)
    return parsed.path, {k: v[0] for k, v in parse_qs(parsed.query).items()}


def validate_date(value, field_name, errors):
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        errors.append(f"{field_name} måste vara i formatet YYYY-MM-DD.")
        return None


def normalize_form(data):
    normalized = {
        key: (value.strip() if isinstance(value, str) else ("" if value is None else str(value).strip()))
        for key, value in data.items()
    }
    for key in (
        "designation",
        "level1",
        "level2",
        "level3",
        "level4",
        "level5",
        "level6",
        "level7",
        "title",
        "description",
        "status",
        "valid_from",
        "valid_to",
        "source_drawing",
        "drawing_revision",
        "change_summary",
        "notes",
        "created_by",
        "approved_by",
        "approved_at",
        "jira_issue_key",
        "jira_decision",
        "parent_object_id",
        "child_kind",
        "mode",
    ):
        normalized.setdefault(key, "")
    return normalized


def render_status_pill(status):
    return f'<span class="pill status-{esc(status)}">{esc(status.replace("_", " "))}</span>'


def fetch_dashboard(conn):
    counts = {
        row["status"]: row["count"]
        for row in conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM (
                SELECT v.*
                FROM object_versions v
                JOIN (
                    SELECT object_id, MAX(version_no) AS max_version
                    FROM object_versions
                    GROUP BY object_id
                ) latest
                  ON latest.object_id = v.object_id
                 AND latest.max_version = v.version_no
            )
            GROUP BY status
            """
        )
    }
    total_objects = conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
    top_only = conn.execute(
        """
        SELECT COUNT(*)
        FROM objects
        WHERE COALESCE(level5, '') = ''
          AND COALESCE(level6, '') = ''
          AND COALESCE(level7, '') = ''
        """
    ).fetchone()[0]
    detailed = total_objects - top_only
    recent = conn.execute(
        """
        SELECT o.id, o.designation, o.title, v.version_no, v.status, v.changed_at
        FROM object_versions v
        JOIN objects o ON o.id = v.object_id
        ORDER BY v.changed_at DESC
        LIMIT 8
        """
    ).fetchall()
    return total_objects, top_only, detailed, counts, recent


def render_dashboard(conn, flash):
    total_objects, top_only, detailed, counts, recent = fetch_dashboard(conn)
    cards = [
        ("Objekt i registret", total_objects, "Alla unika beteckningar."),
        ("Bara nivå 1-4", top_only, "Bra när nivå 5-7 ännu inte är tillsatta."),
        ("Med nivå 5-7", detailed, "Poster där process-, utrustnings- eller kontrollnivå lagts till."),
        ("Väntar godkännande", counts.get("skickad_for_godkannande", 0), "Underlag redo för granskare."),
    ]
    stats_html = "".join(
        f"""
        <article class="card">
          <div class="stat">{value}</div>
          <h2>{label}</h2>
          <div class="muted">{text}</div>
        </article>
        """
        for label, value, text in cards
    )
    if recent:
        rows = "".join(
            f"""
            <tr>
              <td><a class="mono" href="/objects/{row['id']}">{esc(row['designation'])}</a></td>
              <td>{esc(row['title'])}</td>
              <td>v{row['version_no']}</td>
              <td>{render_status_pill(row['status'])}</td>
              <td>{esc(fmt_datetime(row['changed_at']))}</td>
            </tr>
            """
            for row in recent
        )
        recent_table = f"""
        <section class="table-wrap">
          <div class="table-head">
            <h2>Senaste aktivitet</h2>
            <a class="button secondary" href="/objects">Öppna registret</a>
          </div>
          <table>
            <thead>
              <tr>
                <th>Beteckning</th>
                <th>Populärnamn</th>
                <th>Version</th>
                <th>Status</th>
                <th>Ändrad</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </section>
        """
    else:
        recent_table = """
        <section class="notice card">
          <h2>Tomt register</h2>
          <p class="muted">Börja med en grundpost på nivå 1-4 från ritningen. När projekteringen går vidare kan du lägga in nivå 5-7 som fördjupade poster.</p>
          <a class="button" href="/objects/new?mode=base">Skapa första grundposten</a>
        </section>
        """
    body = f"""
    <section class="grid">{stats_html}</section>
    {recent_table}
    <section class="two-col">
      <article class="card">
        <h2>Arbetssätt</h2>
        <p>Excel-filen visar att ni i dag främst jobbar i kedjan driftområde, disciplin, anläggning och funktionsklass. Formuläret är därför uppdelat så att nivå 5-7 ligger som en senare fördjupning.</p>
      </article>
      <article class="card">
        <h2>Spårbarhet</h2>
        <p>Varje version bär med sig datum för skapande, ändring, giltighet, ritningskälla och godkännande. Audit-loggen visar när något lades till eller uppdaterades.</p>
      </article>
    </section>
    """
    return build_page("Översikt", body, flash=flash)


def latest_versions_query():
    return """
    SELECT o.*, v.id AS version_id, v.version_no, v.status, v.valid_from, v.valid_to,
           v.source_drawing, v.drawing_revision, v.changed_at, v.created_by, v.approved_by, v.approved_at,
           v.jira_issue_key, v.jira_decision, v.jira_synced_at, v.jira_sync_status
    FROM objects o
    JOIN object_versions v ON v.object_id = o.id
    JOIN (
        SELECT object_id, MAX(version_no) AS max_version
        FROM object_versions
        GROUP BY object_id
    ) latest
      ON latest.object_id = v.object_id
     AND latest.max_version = v.version_no
    """


def render_objects(conn, query, status, flash):
    sql = latest_versions_query() + " WHERE 1=1 "
    params = []
    if query:
        sql += """
        AND (
            o.designation LIKE ?
            OR o.title LIKE ?
            OR COALESCE(v.source_drawing, '') LIKE ?
        )
        """
        like = f"%{query}%"
        params.extend([like, like, like])
    if status:
        sql += " AND v.status = ? "
        params.append(status)
    sql += " ORDER BY o.designation COLLATE NOCASE"
    rows = conn.execute(sql, params).fetchall()

    search_form = f"""
    <form method="get" action="/objects">
      <h2>Filter</h2>
      <div class="form-grid">
        <label>Sök
          <input type="text" name="q" value="{esc(query)}" placeholder="ToppID, populärnamn eller ritning">
        </label>
        <label>Status
          <select name="status">
            <option value="">Alla</option>
            {''.join(f'<option value="{s}" {"selected" if s == status else ""}>{esc(s.replace("_", " "))}</option>' for s in STATUSES)}
          </select>
        </label>
      </div>
      <div class="inline-actions">
        <button type="submit">Filtrera</button>
        <a class="button secondary" href="/objects">Nollställ</a>
        <a class="button secondary" href="/objects/new?mode=base">Ny grundpost</a>
        <a class="button secondary" href="/objects/new?mode=detail">Ny detaljpost</a>
      </div>
    </form>
    """

    if rows:
        table_rows = "".join(
            f"""
            <tr>
              <td><a class="mono" href="/objects/{row['id']}">{esc(row['designation'])}</a></td>
              <td>{esc(row['title'])}</td>
              <td>{esc(object_scope_label(row))}</td>
              <td>{esc(joined_levels(row, CORE_LEVELS))}</td>
              <td>{esc(joined_levels(row, DETAIL_LEVELS, 'Ej tillsatt'))}</td>
              <td>{render_status_pill(row['status'])}</td>
              <td>{esc(row['approved_by'] or '')}</td>
              <td>{esc(row['source_drawing'] or '')}</td>
            </tr>
            """
            for row in rows
        )
        table = f"""
        <section class="table-wrap">
          <div class="table-head">
            <h2>Register ({len(rows)})</h2>
            <a class="button secondary" href="/export.csv">Exportera CSV</a>
          </div>
          <table>
            <thead>
              <tr>
                <th>ToppID</th>
                <th>Populärnamn</th>
                <th>Typ</th>
                <th>Grundstruktur</th>
                <th>Fördjupning</th>
                <th>Status</th>
                <th>Godkänd av</th>
                <th>Ritning</th>
              </tr>
            </thead>
            <tbody>{table_rows}</tbody>
          </table>
        </section>
        """
    else:
        table = """
        <section class="card">
          <h2>Inga träffar</h2>
          <p class="muted">Justera filter eller skapa en ny registrering.</p>
        </section>
        """
    return build_page("Register", f"{search_form}{table}", active="objects", flash=flash)


def render_object_form(data, errors, action, heading, submit_label, mode="base", parent=None):
    data = normalize_form(data or {})
    generated_designation = build_designation(data)
    error_html = ""
    if errors:
        error_items = "".join(f"<li>{esc(error)}</li>" for error in errors)
        error_html = f"""
        <div class="flash">
          <strong>Kontrollera fälten:</strong>
          <ul>{error_items}</ul>
        </div>
        """
    core_fields = "".join(
        f"""
        <label>{level_label(index)}
          <input type="text" name="level{index}" value="{esc(data[f'level{index}'])}" placeholder="">
        </label>
        """
        for index in CORE_LEVELS
    )
    detail_fields = "".join(
        f"""
        <label>{level_label(index)}
          <input type="text" name="level{index}" value="{esc(data[f'level{index}'])}">
        </label>
        """
        for index in DETAIL_LEVELS
    )
    show_details_open = mode == "detail" or any(data[f"level{index}"] for index in DETAIL_LEVELS)
    child_kind = data.get("child_kind", "")
    focus_name = detail_focus_label(child_kind)
    mode_title = "Ny grundpost för nivå 1-4" if mode == "base" else f"Ny {focus_name.lower()}"
    mode_text = (
        "Utgå från driftområde, disciplin, anläggning och funktionsklass. Låt nivå 5-7 vara tomma tills projekteringen kräver dem."
        if mode == "base"
        else "Använd detta när processenhet, utrustningsenhet eller kontrollenhet börjar tillsättas. Grundkedjan nivå 1-4 ligger kvar och varje underpost får eget populärnamn."
    )
    parent_note = ""
    if parent:
        parent_note = f"""
        <div class="soft-note">
          <strong>Huvudpost</strong>
          <div class="mono">{esc(parent['designation'])}</div>
          <div>{esc(parent['title'])}</div>
          <div class="muted">Grundkedja: {esc(joined_levels(parent, CORE_LEVELS))}</div>
        </div>
        """
    return f"""
    {error_html}
    <form method="post" action="{esc(action)}">
      <input type="hidden" name="mode" value="{esc(mode)}">
      <input type="hidden" name="parent_object_id" value="{esc(data.get('parent_object_id', ''))}">
      <input type="hidden" name="child_kind" value="{esc(child_kind)}">
      <h2>{esc(heading)}</h2>
      <div class="soft-note">
        <span class="eyebrow">{esc(mode_title)}</span>
        <strong>{esc(mode_text)}</strong>
        <div class="muted">Nuvarande grundkedja: {esc(joined_levels(data, CORE_LEVELS, 'Inte ifylld ännu'))}</div>
        <div class="token-line">
          <span class="token">{esc(level_label(1))}: {esc(data['level1'] or '-')}</span>
          <span class="token">{esc(level_label(2))}: {esc(data['level2'] or '-')}</span>
          <span class="token">{esc(level_label(3))}: {esc(data['level3'] or '-')}</span>
          <span class="token">{esc(level_label(4))}: {esc(data['level4'] or '-')}</span>
        </div>
      </div>
      {parent_note}

      <section class="form-section">
        <h3>Huvudsystem</h3>
        <p>Populärnamn och nivå 4 är det viktigaste här. Nivå 1-3 är toppnod och är ofta återkommande.</p>
        <div class="form-grid">
          <label>Populärnamn *
            <input type="text" name="title" value="{esc(data['title'])}" required>
          </label>
          <label>{level_label(4)} *
            <input class="mono" type="text" name="level4" value="{esc(data['level4'])}" required>
          </label>
          <label>ToppID / full beteckning
            <input class="mono" type="text" value="{esc(generated_designation or 'Genereras automatiskt när nivåerna är ifyllda')}" readonly>
          </label>
        </div>
        <div class="muted">ToppID är inte fri text utan byggs automatiskt av nivå 1-7 med punkt mellan nivåerna.</div>
      </section>

      <section class="form-section">
        <h3>Toppnod nivå 1-3</h3>
        <p>Driftområde, disciplin och funktions-ID för anläggning är toppnoden. Den får återkomma mellan flera huvudsystem.</p>
        <div class="form-grid">
          <label>{level_label(1)}
            <input type="text" name="level1" value="{esc(data['level1'])}">
          </label>
          <label>{level_label(2)}
            <input type="text" name="level2" value="{esc(data['level2'])}">
          </label>
          <label>{level_label(3)}
            <input type="text" name="level3" value="{esc(data['level3'])}">
          </label>
          <label>Registrerad av
            <input type="text" name="created_by" value="{esc(data['created_by'])}" placeholder="Ditt namn eller roll">
          </label>
        </div>
      </section>

      <details class="form-section" {'open' if show_details_open else ''}>
        <summary>Fördjupning nivå 5-7</summary>
        <div class="details-body">
          <p>Lämna tomt tills projekteringen har kommit dit. Här registreras processenhet, utrustningsenhet och kontrollenhet. Varje rad får sitt eget populärnamn.</p>
          <div class="form-grid">{detail_fields}</div>
        </div>
      </details>

      <section class="form-section">
        <h3>Beskrivning och spårbarhet</h3>
        <p>Här lägger du källan från ritningen och den versionsinformation som behövs för historik och granskning.</p>
        <label>Beskrivning / förtydligande
          <textarea name="description">{esc(data['description'])}</textarea>
        </label>
        <div class="form-grid">
          <label>Status
          <select name="status">
            {''.join(f'<option value="{s}" {"selected" if s == data["status"] else ""}>{esc(s.replace("_", " "))}</option>' for s in STATUSES)}
          </select>
        </label>
        <label>Gäller från
          <input type="date" name="valid_from" value="{esc(date_input_value(data['valid_from']))}">
        </label>
        <label>Gäller till
          <input type="date" name="valid_to" value="{esc(date_input_value(data['valid_to']))}">
        </label>
        <label>Godkänd av
          <input type="text" name="approved_by" value="{esc(data['approved_by'])}">
        </label>
        <label>Godkänd datum
          <input type="date" name="approved_at" value="{esc(date_input_value(data['approved_at']))}">
        </label>
        <label>Ritning
          <input type="text" name="source_drawing" value="{esc(data['source_drawing'])}">
        </label>
        <label>Ritningsrevision
          <input type="text" name="drawing_revision" value="{esc(data['drawing_revision'])}">
        </label>
        </div>
        <label>Ändringssammanfattning
          <textarea name="change_summary">{esc(data['change_summary'])}</textarea>
        </label>
        <label>Versionsanteckning
          <textarea name="notes">{esc(data['notes'])}</textarea>
        </label>
      </section>

      <section class="form-section">
        <h3>Jira och beslut</h3>
        <p>Om posten hör ihop med ett Jira-ärende kan du spara ärendenyckeln här. Beslutsfältet kan fyllas i manuellt eller synkas via Jira API när miljövariablerna är satta.</p>
        <div class="form-grid">
          <label>Jira-ärende
            <input type="text" name="jira_issue_key" value="{esc(data['jira_issue_key'])}" placeholder="PROJ-123">
          </label>
          <label>Beslut
            <input type="text" name="jira_decision" value="{esc(data['jira_decision'])}" placeholder="Godkänd, Avvaktas, Nekad ...">
          </label>
        </div>
      </section>
      <div class="inline-actions">
        <button type="submit">{esc(submit_label)}</button>
        <a class="button secondary" href="/objects">Avbryt</a>
      </div>
    </form>
    """


def render_new_object(conn, data=None, errors=None, flash="", mode="base", parent_id=""):
    defaults = {
        "status": "registrerad",
        "valid_from": "",
        "valid_to": "",
        "approved_at": "",
        "parent_object_id": "",
        "child_kind": "",
    }
    if data:
        defaults.update(data)
    parent = None
    if defaults.get("parent_object_id"):
        try:
            parent = get_object(conn, int(defaults["parent_object_id"]))
        except ValueError:
            parent = None
    elif parent_id:
        try:
            parent = get_object(conn, int(parent_id))
        except ValueError:
            parent = None
        if parent:
            defaults["parent_object_id"] = str(parent["id"])
            for index in CORE_LEVELS:
                defaults[f"level{index}"] = parent[f"level{index}"] or ""
            if mode == "detail" and not defaults.get("title"):
                defaults["title"] = ""
    elif not any(defaults.get(f"level{index}") for index in (1, 2, 3)):
        recent_top_node = get_recent_top_node(conn)
        if recent_top_node:
            for index in (1, 2, 3):
                defaults[f"level{index}"] = recent_top_node[f"level{index}"] or ""
    heading = "Ny grundpost" if mode == "base" else "Ny detaljpost"
    if mode == "detail" and defaults.get("child_kind"):
        heading = f"Ny {detail_focus_label(defaults['child_kind']).lower()}"
    body = render_object_form(defaults, errors or [], "/objects/new", heading, "Spara objekt", mode=mode, parent=parent)
    return build_page("Ny registrering", body, active="new", flash=flash)


def create_object(conn, data):
    errors = []
    data = normalize_form(data)
    if not data["title"]:
        errors.append("Populärnamn måste fyllas i.")
    if not data["level4"]:
        errors.append("Funktionsklass / huvudsystem på nivå 4 måste fyllas i.")
    data["designation"] = build_designation(data)
    if not data["designation"]:
        errors.append("ToppID kunde inte byggas. Fyll i nivåerna som behövs.")
    if data["status"] not in STATUSES:
        errors.append("Ogiltig status.")
    valid_from = validate_date(data["valid_from"], "Gäller från", errors)
    valid_to = validate_date(data["valid_to"], "Gäller till", errors)
    approved_at = validate_date(data["approved_at"], "Godkänd datum", errors)
    parent_object_id = None
    if data["parent_object_id"]:
        try:
            parent_object_id = int(data["parent_object_id"])
        except ValueError:
            errors.append("Ogiltig huvudpost.")
        else:
            if not get_object(conn, parent_object_id):
                errors.append("Huvudposten finns inte längre.")
    if data["mode"] == "detail" and not any(data[f"level{index}"] for index in DETAIL_LEVELS):
        errors.append("För en detaljpost behöver minst processenhet, utrustningsenhet eller kontrollenhet fyllas i.")
    if valid_from and valid_to and valid_to < valid_from:
        errors.append("Gäller till får inte vara tidigare än gäller från.")
    if errors:
        return errors

    timestamp = now_iso()
    try:
        cursor = conn.execute(
            """
            INSERT INTO objects(
                designation, parent_object_id, level1, level2, level3, level4, level5, level6, level7,
                title, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["designation"],
                parent_object_id,
                data["level1"],
                data["level2"],
                data["level3"],
                data["level4"],
                data["level5"],
                data["level6"],
                data["level7"],
                data["title"],
                data["description"],
                timestamp,
                timestamp,
            ),
        )
        object_id = cursor.lastrowid
        version_cursor = conn.execute(
            """
            INSERT INTO object_versions(
                object_id, version_no, status, valid_from, valid_to, source_drawing, drawing_revision,
                change_summary, notes, created_at, created_by, changed_at, approved_by, approved_at,
                jira_issue_key, jira_decision, jira_synced_at, jira_sync_status
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                object_id,
                data["status"],
                valid_from,
                valid_to,
                data["source_drawing"],
                data["drawing_revision"],
                data["change_summary"],
                data["notes"],
                timestamp,
                data["created_by"],
                timestamp,
                data["approved_by"],
                approved_at,
                data["jira_issue_key"],
                data["jira_decision"],
                "",
                "",
            ),
        )
        version_id = version_cursor.lastrowid
        if data["jira_issue_key"] and jira_ready():
            try:
                sync_version_from_jira(conn, version_id)
            except ValueError:
                pass
        record_event(
            conn,
            object_id,
            version_id,
            "created",
            data["created_by"],
            f"Objekt {data['designation']} skapades i version 1.",
        )
        conn.commit()
        return []
    except sqlite3.IntegrityError:
        conn.rollback()
        return ["Den fullständiga beteckningen finns redan i registret."]


def get_object(conn, object_id):
    return conn.execute("SELECT * FROM objects WHERE id = ?", (object_id,)).fetchone()


def get_child_objects(conn, parent_object_id):
    return conn.execute(
        latest_versions_query() + """
        WHERE o.parent_object_id = ?
        ORDER BY
          CASE
            WHEN COALESCE(o.level7, '') <> '' THEN 3
            WHEN COALESCE(o.level6, '') <> '' THEN 2
            WHEN COALESCE(o.level5, '') <> '' THEN 1
            ELSE 0
          END,
          o.level5, o.level6, o.level7, o.designation
        """,
        (parent_object_id,),
    ).fetchall()


def get_recent_top_node(conn):
    return conn.execute(
        """
        SELECT level1, level2, level3
        FROM objects
        WHERE COALESCE(level1, '') <> ''
           OR COALESCE(level2, '') <> ''
           OR COALESCE(level3, '') <> ''
        ORDER BY updated_at DESC
        LIMIT 1
        """
    ).fetchone()


def get_versions(conn, object_id):
    return conn.execute(
        """
        SELECT *
        FROM object_versions
        WHERE object_id = ?
        ORDER BY version_no DESC
        """,
        (object_id,),
    ).fetchall()


def get_audit_log(conn, object_id):
    return conn.execute(
        """
        SELECT *
        FROM audit_log
        WHERE object_id = ?
        ORDER BY event_time DESC
        LIMIT 20
        """,
        (object_id,),
    ).fetchall()


def render_object_detail(conn, object_id, flash):
    obj = get_object(conn, object_id)
    if not obj:
        return not_found_page()
    parent = get_object(conn, obj["parent_object_id"]) if obj["parent_object_id"] else None
    versions = get_versions(conn, object_id)
    audit_rows = get_audit_log(conn, object_id)
    child_rows = get_child_objects(conn, object_id)
    latest = versions[0] if versions else None
    core_meta = "".join(
        f"""
        <div>
          <strong>{level_label(index)}</strong>
          <span class="mono">{esc(obj[f'level{index}'] or '-')}</span>
        </div>
        """
        for index in CORE_LEVELS
    )
    detail_meta = "".join(
        f"""
        <div>
          <strong>{level_label(index)}</strong>
          <span class="mono">{esc(obj[f'level{index}'] or 'Ej tillsatt')}</span>
        </div>
        """
        for index in DETAIL_LEVELS
    )
    version_rows = "".join(
        f"""
        <tr>
          <td>v{row['version_no']}</td>
          <td>{render_status_pill(row['status'])}</td>
          <td>{esc(fmt_date(row['valid_from']))}</td>
          <td>{esc(fmt_date(row['valid_to']))}</td>
          <td>{esc(row['approved_by'] or '')}</td>
          <td>{esc(fmt_date(row['approved_at']))}</td>
          <td>{esc(row['source_drawing'] or '')}</td>
          <td>{esc(fmt_datetime(row['changed_at']))}</td>
        </tr>
        """
        for row in versions
    ) or '<tr><td colspan="8" class="empty">Inga versioner ännu.</td></tr>'
    audit_html = "".join(
        f"""
        <tr>
          <td>{esc(fmt_datetime(row['event_time']))}</td>
          <td>{esc(row['event_type'])}</td>
          <td>{esc(row['actor'] or '')}</td>
          <td>{esc(row['details'] or '')}</td>
        </tr>
        """
        for row in audit_rows
    ) or '<tr><td colspan="4" class="empty">Ingen historik ännu.</td></tr>'
    latest_box = ""
    if latest:
        jira_block = ""
        if latest["jira_issue_key"] or latest["jira_decision"]:
            jira_block = f"""
            <div class="meta-list" style="margin-top:14px;">
              <div><strong>Jira-ärende</strong>{esc(latest['jira_issue_key'] or 'Ej satt')}</div>
              <div><strong>Beslut</strong>{esc(latest['jira_decision'] or 'Ej satt')}</div>
              <div><strong>Senast synkad</strong>{esc(fmt_datetime(latest['jira_synced_at']))}</div>
              <div><strong>Jira-status</strong>{esc(latest['jira_sync_status'] or 'Ej satt')}</div>
            </div>
            """
        sync_action = ""
        if latest["jira_issue_key"]:
            sync_action = f"""
            <form method="post" action="/objects/{object_id}/jira-sync">
              <button type="submit" class="secondary">Synka Jira-beslut</button>
            </form>
            """
        latest_box = f"""
        <article class="card">
          <h2>Senaste version</h2>
          <div class="meta-list">
            <div><strong>Version</strong>v{latest['version_no']}</div>
            <div><strong>Status</strong>{render_status_pill(latest['status'])}</div>
            <div><strong>Godkänd av</strong>{esc(latest['approved_by'] or 'Ej satt')}</div>
            <div><strong>Godkänd datum</strong>{esc(fmt_date(latest['approved_at']))}</div>
            <div><strong>Gäller från</strong>{esc(fmt_date(latest['valid_from']))}</div>
            <div><strong>Gäller till</strong>{esc(fmt_date(latest['valid_to']))}</div>
            <div><strong>Ritning</strong>{esc(latest['source_drawing'] or 'Ej satt')}</div>
            <div><strong>Revision</strong>{esc(latest['drawing_revision'] or 'Ej satt')}</div>
            <div><strong>Skapad av</strong>{esc(latest['created_by'] or 'Ej satt')}</div>
            <div><strong>Senast ändrad</strong>{esc(fmt_datetime(latest['changed_at']))}</div>
          </div>
          {jira_block}
          <p><strong>Ändringssammanfattning:</strong><br>{esc(latest['change_summary'] or 'Ingen sammanfattning angiven.')}</p>
          <p><strong>Anteckningar:</strong><br>{esc(latest['notes'] or 'Inga anteckningar.')}</p>
          <div class="inline-actions">{sync_action}</div>
        </article>
        """
    body = f"""
    <section class="two-col">
      <article class="card">
        <div class="inline-actions" style="justify-content:space-between;">
          <div>
            <span class="eyebrow">{esc(object_scope_label(obj))}</span>
            <h2 style="margin-bottom:4px;">{esc(obj['title'])}</h2>
            <div class="mono">{esc(obj['designation'])}</div>
          </div>
          <a class="button" href="/objects/{object_id}/versions/new">Ny version</a>
        </div>
        <p>{esc(obj['description'] or 'Ingen beskrivning eller förtydligande angivet.')}</p>
        <div class="meta-list">
          <div><strong>Skapad</strong>{esc(fmt_datetime(obj['created_at']))}</div>
          <div><strong>Senast uppdaterad</strong>{esc(fmt_datetime(obj['updated_at']))}</div>
        </div>
        {f'<p><strong>Huvudpost:</strong> <a href="/objects/{parent["id"]}">{esc(parent["designation"])} - {esc(parent["title"])}</a></p>' if parent else ''}
        <h2 style="margin-top:18px;">Grundstruktur</h2>
        <div class="meta-list">{core_meta}</div>
        <h2 style="margin-top:18px;">Fördjupning nivå 5-7</h2>
        <div class="meta-list">{detail_meta}</div>
      </article>
      {latest_box}
    </section>
    """
    if is_main_object(obj):
        child_table_rows = "".join(
            f"""
            <tr>
              <td>{esc(object_scope_label(row))}</td>
              <td><a class="mono" href="/objects/{row['id']}">{esc(row['designation'])}</a></td>
              <td>{esc(row['title'])}</td>
              <td>{esc(level_value(row, 5) or '-')}</td>
              <td>{esc(level_value(row, 6) or '-')}</td>
              <td>{esc(level_value(row, 7) or '-')}</td>
              <td>{esc(row['approved_by'] or '')}</td>
            </tr>
            """
            for row in child_rows
        ) or '<tr><td colspan="7" class="empty">Inga underposter ännu. Lägg till processenhet, utrustningsenhet eller kontrollenhet under den här funktionsklassen.</td></tr>'
        body += f"""
        <section class="table-wrap">
          <div class="table-head">
            <h2>Underposter under funktionsklass</h2>
            <div class="inline-actions">
              <a class="button secondary" href="/objects/new?mode=detail&parent_id={object_id}&child_kind=level5">Ny processenhet</a>
              <a class="button secondary" href="/objects/new?mode=detail&parent_id={object_id}&child_kind=level6">Ny utrustningsenhet</a>
              <a class="button secondary" href="/objects/new?mode=detail&parent_id={object_id}&child_kind=level7">Ny kontrollenhet</a>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Typ</th>
                <th>ToppID</th>
                <th>Populärnamn</th>
                <th>Processenhet</th>
                <th>Utrustningsenhet</th>
                <th>Kontrollenhet</th>
                <th>Godkänd av</th>
              </tr>
            </thead>
            <tbody>{child_table_rows}</tbody>
          </table>
        </section>
        """
    body += f"""
    <section class="table-wrap">
      <div class="table-head">
        <h2>Versioner</h2>
      </div>
      <table>
        <thead>
          <tr>
            <th>Version</th>
            <th>Status</th>
            <th>Gäller från</th>
            <th>Gäller till</th>
            <th>Godkänd av</th>
            <th>Godkänd datum</th>
            <th>Ritning</th>
            <th>Ändrad</th>
          </tr>
        </thead>
        <tbody>{version_rows}</tbody>
      </table>
    </section>
    <section class="table-wrap">
      <div class="table-head">
        <h2>Audit-logg</h2>
      </div>
      <table>
        <thead>
          <tr>
            <th>Tid</th>
            <th>Händelse</th>
            <th>Aktör</th>
            <th>Detalj</th>
          </tr>
        </thead>
        <tbody>{audit_html}</tbody>
      </table>
    </section>
    """
    return build_page(obj["designation"], body, active="objects", flash=flash)


def render_version_form(obj, data, errors):
    data = normalize_form(data or {})
    errors_html = ""
    if errors:
        error_items = "".join(f"<li>{esc(error)}</li>" for error in errors)
        errors_html = f"""
        <div class="flash">
          <strong>Kontrollera fälten:</strong>
          <ul>{error_items}</ul>
        </div>
        """
    return f"""
    {errors_html}
    <form method="post" action="/objects/{obj['id']}/versions/new">
      <h2>Ny version för {esc(obj['designation'])}</h2>
      <div class="soft-note">
        <strong>{esc(obj['title'])}</strong>
        <div class="muted">Grundstruktur: {esc(joined_levels(obj, CORE_LEVELS))}</div>
        <div class="muted">Fördjupning: {esc(joined_levels(obj, DETAIL_LEVELS, 'Ej tillsatt ännu'))}</div>
      </div>
      <section class="form-section">
        <h3>Godkännande och giltighet</h3>
        <p>Här ser du tydligt vem som godkänt versionen och när den gäller.</p>
        <div class="form-grid">
          <label>Status
            <select name="status">
              {''.join(f'<option value="{s}" {"selected" if s == data["status"] else ""}>{esc(s.replace("_", " "))}</option>' for s in STATUSES)}
            </select>
          </label>
          <label>Gäller från
            <input type="date" name="valid_from" value="{esc(date_input_value(data['valid_from']))}">
          </label>
          <label>Gäller till
            <input type="date" name="valid_to" value="{esc(date_input_value(data['valid_to']))}">
          </label>
          <label>Godkänd av
            <input type="text" name="approved_by" value="{esc(data['approved_by'])}">
          </label>
          <label>Godkänd datum
            <input type="date" name="approved_at" value="{esc(date_input_value(data['approved_at']))}">
          </label>
        </div>
      </section>
      <section class="form-section">
        <h3>Källa och versionsnotering</h3>
        <div class="form-grid">
          <label>Ritning
            <input type="text" name="source_drawing" value="{esc(data['source_drawing'])}">
          </label>
          <label>Ritningsrevision
            <input type="text" name="drawing_revision" value="{esc(data['drawing_revision'])}">
          </label>
          <label>Skapad av
            <input type="text" name="created_by" value="{esc(data['created_by'])}">
          </label>
        </div>
        <label>Ändringssammanfattning
          <textarea name="change_summary">{esc(data['change_summary'])}</textarea>
        </label>
        <label>Versionsanteckning
          <textarea name="notes">{esc(data['notes'])}</textarea>
        </label>
      </section>
      <section class="form-section">
        <h3>Jira och beslut</h3>
        <p>Här kan du koppla versionen till ett Jira-ärende och lagra beslutet från ert beslutsfält.</p>
        <div class="form-grid">
          <label>Jira-ärende
            <input type="text" name="jira_issue_key" value="{esc(data['jira_issue_key'])}" placeholder="PROJ-123">
          </label>
          <label>Beslut
            <input type="text" name="jira_decision" value="{esc(data['jira_decision'])}">
          </label>
        </div>
      </section>
      <div class="inline-actions">
        <button type="submit">Spara ny version</button>
        <a class="button secondary" href="/objects/{obj['id']}">Tillbaka</a>
      </div>
    </form>
    """


def render_new_version(conn, object_id, data=None, errors=None, flash=""):
    obj = get_object(conn, object_id)
    if not obj:
        return not_found_page()
    latest = conn.execute(
        """
        SELECT *
        FROM object_versions
        WHERE object_id = ?
        ORDER BY version_no DESC
        LIMIT 1
        """,
        (object_id,),
    ).fetchone()
    defaults = {
        "status": latest["status"] if latest else "registrerad",
        "valid_from": latest["valid_from"] if latest else "",
        "valid_to": latest["valid_to"] if latest else "",
        "source_drawing": latest["source_drawing"] if latest else "",
        "drawing_revision": latest["drawing_revision"] if latest else "",
        "change_summary": "",
        "notes": latest["notes"] if latest else "",
        "created_by": latest["created_by"] if latest else "",
        "approved_by": latest["approved_by"] if latest else "",
        "approved_at": latest["approved_at"] if latest else "",
        "jira_issue_key": latest["jira_issue_key"] if latest else "",
        "jira_decision": latest["jira_decision"] if latest else "",
    }
    if data:
        defaults.update(data)
    body = render_version_form(obj, defaults, errors or [])
    return build_page("Ny version", body, active="objects", flash=flash)


def create_version(conn, object_id, data):
    errors = []
    obj = get_object(conn, object_id)
    if not obj:
        return ["Objektet finns inte."]
    data = normalize_form(data)
    if data["status"] not in STATUSES:
        errors.append("Ogiltig status.")
    valid_from = validate_date(data["valid_from"], "Gäller från", errors)
    valid_to = validate_date(data["valid_to"], "Gäller till", errors)
    approved_at = validate_date(data["approved_at"], "Godkänd datum", errors)
    if valid_from and valid_to and valid_to < valid_from:
        errors.append("Gäller till får inte vara tidigare än gäller från.")
    if errors:
        return errors
    latest = conn.execute(
        "SELECT COALESCE(MAX(version_no), 0) FROM object_versions WHERE object_id = ?",
        (object_id,),
    ).fetchone()[0]
    version_no = latest + 1
    timestamp = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO object_versions(
            object_id, version_no, status, valid_from, valid_to, source_drawing, drawing_revision,
            change_summary, notes, created_at, created_by, changed_at, approved_by, approved_at,
            jira_issue_key, jira_decision, jira_synced_at, jira_sync_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            object_id,
            version_no,
            data["status"],
            valid_from,
            valid_to,
            data["source_drawing"],
            data["drawing_revision"],
            data["change_summary"],
            data["notes"],
            timestamp,
            data["created_by"],
            timestamp,
            data["approved_by"],
            approved_at,
            data["jira_issue_key"],
            data["jira_decision"],
            "",
            "",
        ),
    )
    conn.execute(
        "UPDATE objects SET updated_at = ? WHERE id = ?",
        (timestamp, object_id),
    )
    if data["jira_issue_key"] and jira_ready():
        try:
            sync_version_from_jira(conn, cursor.lastrowid)
        except ValueError:
            pass
    record_event(
        conn,
        object_id,
        cursor.lastrowid,
        "version_created",
        data["created_by"],
        f"Version {version_no} skapades med status {data['status']}.",
    )
    conn.commit()
    return []


def render_checks(conn, flash):
    main_system_clashes = conn.execute(
        """
        SELECT level1, level2, level3, level4,
               COUNT(*) AS total,
               GROUP_CONCAT(designation, ', ') AS designations
        FROM objects
        WHERE COALESCE(level4, '') <> ''
          AND COALESCE(level5, '') = ''
          AND COALESCE(level6, '') = ''
          AND COALESCE(level7, '') = ''
        GROUP BY level1, level2, level3, level4
        HAVING COUNT(*) > 1
        ORDER BY total DESC, designations
        """
    ).fetchall()
    process_clashes = conn.execute(
        """
        SELECT parent_object_id, level5 AS node_code,
               COUNT(*) AS total,
               GROUP_CONCAT(designation, ', ') AS designations
        FROM objects
        WHERE parent_object_id IS NOT NULL
          AND COALESCE(level5, '') <> ''
        GROUP BY parent_object_id, level5
        HAVING COUNT(*) > 1
        ORDER BY total DESC, designations
        """
    ).fetchall()
    equipment_clashes = conn.execute(
        """
        SELECT parent_object_id, level6 AS node_code,
               COUNT(*) AS total,
               GROUP_CONCAT(designation, ', ') AS designations
        FROM objects
        WHERE parent_object_id IS NOT NULL
          AND COALESCE(level6, '') <> ''
        GROUP BY parent_object_id, level6
        HAVING COUNT(*) > 1
        ORDER BY total DESC, designations
        """
    ).fetchall()
    control_clashes = conn.execute(
        """
        SELECT parent_object_id, level7 AS node_code,
               COUNT(*) AS total,
               GROUP_CONCAT(designation, ', ') AS designations
        FROM objects
        WHERE parent_object_id IS NOT NULL
          AND COALESCE(level7, '') <> ''
        GROUP BY parent_object_id, level7
        HAVING COUNT(*) > 1
        ORDER BY total DESC, designations
        """
    ).fetchall()
    expired = conn.execute(
        """
        SELECT o.id, o.designation, o.title, v.version_no, v.valid_to
        FROM object_versions v
        JOIN objects o ON o.id = v.object_id
        JOIN (
            SELECT object_id, MAX(version_no) AS max_version
            FROM object_versions
            GROUP BY object_id
        ) latest
          ON latest.object_id = v.object_id
         AND latest.max_version = v.version_no
        WHERE v.status <> 'ur_bruk'
          AND v.valid_to IS NOT NULL
          AND v.valid_to <> ''
          AND v.valid_to < date('now')
        ORDER BY v.valid_to ASC
        """
    ).fetchall()
    missing_source = conn.execute(
        """
        SELECT o.id, o.designation, o.title, v.version_no
        FROM object_versions v
        JOIN objects o ON o.id = v.object_id
        JOIN (
            SELECT object_id, MAX(version_no) AS max_version
            FROM object_versions
            GROUP BY object_id
        ) latest
          ON latest.object_id = v.object_id
         AND latest.max_version = v.version_no
        WHERE COALESCE(v.source_drawing, '') = ''
        ORDER BY o.designation
        """
    ).fetchall()
    main_system_rows = "".join(
        f"""
        <tr>
          <td class="mono">{esc(' / '.join(filter(None, [row['level1'], row['level2'], row['level3']])) or '(tom toppnod)')}</td>
          <td class="mono">{esc(row['level4'])}</td>
          <td>{row['total']}</td>
          <td>{esc(row['designations'])}</td>
        </tr>
        """
        for row in main_system_clashes
    ) or '<tr><td colspan="4" class="empty">Inga dubletter på huvudsystem (nivå 4) hittades.</td></tr>'

    def child_clash_rows(rows, label):
        rendered = "".join(
            f"""
            <tr>
              <td>{esc(label)}</td>
              <td>{row['parent_object_id']}</td>
              <td class="mono">{esc(row['node_code'])}</td>
              <td>{row['total']}</td>
              <td>{esc(row['designations'])}</td>
            </tr>
            """
            for row in rows
        )
        return rendered

    child_rows = (
        child_clash_rows(process_clashes, "Processenhet")
        + child_clash_rows(equipment_clashes, "Utrustningsenhet")
        + child_clash_rows(control_clashes, "Kontrollenhet")
    ) or '<tr><td colspan="5" class="empty">Inga krockar på löpnummer i underposter hittades.</td></tr>'

    exact_rows = "".join(
        f"""
        <tr>
          <td class="mono">{esc(' | '.join(filter(None, [row['level1'], row['level2'], row['level3'], row['level4'], row['level5'], row['level6'], row['level7']])) or '(tom nivåsträng)')}</td>
          <td>{row['title']}</td>
          <td>{esc(object_scope_label(row))}</td>
        </tr>
        """
        for row in conn.execute(latest_versions_query() + " ORDER BY o.designation").fetchall()
    )
    expired_rows = "".join(
        f"""
        <tr>
          <td><a class="mono" href="/objects/{row['id']}">{esc(row['designation'])}</a></td>
          <td>{esc(row['title'])}</td>
          <td>v{row['version_no']}</td>
          <td>{esc(fmt_date(row['valid_to']))}</td>
        </tr>
        """
        for row in expired
    ) or '<tr><td colspan="4" class="empty">Inga poster med passerad giltighetstid hittades.</td></tr>'
    missing_rows = "".join(
        f"""
        <tr>
          <td><a class="mono" href="/objects/{row['id']}">{esc(row['designation'])}</a></td>
          <td>{esc(row['title'])}</td>
          <td>v{row['version_no']}</td>
        </tr>
        """
        for row in missing_source
    ) or '<tr><td colspan="3" class="empty">Alla senaste versioner har ritningskälla angiven.</td></tr>'
    body = f"""
    <section class="grid">
      <article class="card">
        <div class="stat">{len(main_system_clashes)}</div>
        <h2>Huvudsystem nivå 4</h2>
        <p class="muted">Toppnoden nivå 1-3 får upprepas. Det som inte får krocka här är huvudsystemets kod på nivå 4.</p>
      </article>
      <article class="card">
        <div class="stat">{len(process_clashes) + len(equipment_clashes) + len(control_clashes)}</div>
        <h2>Löpnummer i underposter</h2>
        <p class="muted">Visar krockar på processenhet, utrustningsenhet eller kontrollenhet under samma huvudpost.</p>
      </article>
      <article class="card">
        <div class="stat">{len(expired)}</div>
        <h2>Passerad giltighet</h2>
        <p class="muted">Senaste versionen har slutdatum men är inte markerad som ur bruk.</p>
      </article>
      <article class="card">
        <div class="stat">{len(missing_source)}</div>
        <h2>Saknar ritningskälla</h2>
        <p class="muted">Bra kontroll före granskning eller publicering.</p>
      </article>
    </section>
    <section class="table-wrap">
      <div class="table-head"><h2>Dubletter på huvudsystem nivå 4</h2></div>
      <table>
        <thead>
          <tr>
            <th>Toppnod nivå 1-3</th>
            <th>Huvudsystem</th>
            <th>Antal</th>
            <th>Beteckningar</th>
          </tr>
        </thead>
        <tbody>{main_system_rows}</tbody>
      </table>
    </section>
    <section class="table-wrap">
      <div class="table-head"><h2>Krockar på löpnummer i underposter</h2></div>
      <table>
        <thead>
          <tr>
            <th>Typ</th>
            <th>Huvudpost-id</th>
            <th>Löpnummer</th>
            <th>Antal</th>
            <th>Beteckningar</th>
          </tr>
        </thead>
        <tbody>{child_rows}</tbody>
      </table>
    </section>
    <section class="table-wrap">
      <div class="table-head"><h2>Passerad giltighet utan ur bruk</h2></div>
      <table>
        <thead>
          <tr>
            <th>Beteckning</th>
            <th>Benämning</th>
            <th>Version</th>
            <th>Gäller till</th>
          </tr>
        </thead>
        <tbody>{expired_rows}</tbody>
      </table>
    </section>
    <section class="table-wrap">
      <div class="table-head"><h2>Saknar ritningskälla</h2></div>
      <table>
        <thead>
          <tr>
            <th>Beteckning</th>
            <th>Benämning</th>
            <th>Version</th>
          </tr>
        </thead>
        <tbody>{missing_rows}</tbody>
      </table>
    </section>
    """
    return build_page("Krockkontroll", body, active="checks", flash=flash)


def render_csv(conn):
    rows = conn.execute(
        """
        SELECT
            o.designation,
            o.title,
            o.level1,
            o.level2,
            o.level3,
            o.level4,
            o.level5,
            o.level6,
            o.level7,
            o.description,
            v.version_no,
            v.status,
            v.valid_from,
            v.valid_to,
            v.source_drawing,
            v.drawing_revision,
            v.created_by,
            v.created_at,
            v.approved_by,
            v.approved_at,
            v.change_summary,
            v.notes
        FROM objects o
        JOIN object_versions v ON v.object_id = o.id
        ORDER BY o.designation COLLATE NOCASE, v.version_no DESC
        """
    ).fetchall()
    headers = [
        "designation",
        "title",
        "level1",
        "level2",
        "level3",
        "level4",
        "level5",
        "level6",
        "level7",
        "description",
        "version_no",
        "status",
        "valid_from",
        "valid_to",
        "source_drawing",
        "drawing_revision",
        "created_by",
        "created_at",
        "approved_by",
        "approved_at",
        "change_summary",
        "notes",
    ]
    output = [";".join(headers)]
    for row in rows:
        output.append(
            ";".join(
                (str(row[key]).replace("\n", " ").replace("\r", " ") if row[key] is not None else "")
                for key in headers
            )
        )
    return "\n".join(output).encode("utf-8-sig")


def not_found_page():
    body = """
    <section class="card">
      <h2>Sidan hittades inte</h2>
      <p class="muted">Kontrollera adressen eller gå tillbaka till registret.</p>
      <a class="button secondary" href="/">Till översikten</a>
    </section>
    """
    return build_page("Hittades inte", body)


class RegistryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        init_db()
        path, params = get_query_params(self)
        with get_connection() as conn:
            if path == "/":
                self.respond_html(render_dashboard(conn, params.get("flash", "")))
                return
            if path == "/objects":
                self.respond_html(
                    render_objects(conn, params.get("q", ""), params.get("status", ""), params.get("flash", ""))
                )
                return
            if path == "/objects/new":
                self.respond_html(
                    render_new_object(
                        conn,
                        flash=params.get("flash", ""),
                        mode=params.get("mode", "base"),
                        parent_id=params.get("parent_id", ""),
                        data={"child_kind": params.get("child_kind", "")},
                    )
                )
                return
            if path.startswith("/objects/") and path.endswith("/versions/new"):
                object_id = self.extract_object_id(path, suffix="/versions/new")
                if object_id is None:
                    self.respond_html(not_found_page(), status=404)
                    return
                self.respond_html(render_new_version(conn, object_id, flash=params.get("flash", "")))
                return
            if path.startswith("/objects/"):
                object_id = self.extract_object_id(path)
                if object_id is None:
                    self.respond_html(not_found_page(), status=404)
                    return
                self.respond_html(render_object_detail(conn, object_id, params.get("flash", "")))
                return
            if path == "/checks":
                self.respond_html(render_checks(conn, params.get("flash", "")))
                return
            if path == "/export.csv":
                payload = render_csv(conn)
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="referensbeteckningar.csv"')
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
        self.respond_html(not_found_page(), status=404)

    def do_POST(self):
        init_db()
        path, _ = get_query_params(self)
        data = parse_post_data(self)
        with get_connection() as conn:
            if path == "/objects/new":
                errors = create_object(conn, data)
                if errors:
                    self.respond_html(
                        render_new_object(conn, data=data, errors=errors, mode=data.get("mode", "base")),
                        status=400,
                    )
                    return
                redirect(self, "/objects?flash=" + quote("Objektet skapades och första versionen sparades."))
                return
            if path.startswith("/objects/") and path.endswith("/versions/new"):
                object_id = self.extract_object_id(path, suffix="/versions/new")
                if object_id is None:
                    self.respond_html(not_found_page(), status=404)
                    return
                errors = create_version(conn, object_id, data)
                if errors:
                    self.respond_html(render_new_version(conn, object_id, data=data, errors=errors), status=400)
                    return
                redirect(
                    self,
                    f"/objects/{object_id}?flash=" + quote("Ny version sparades i historiken."),
                )
                return
            if path.startswith("/objects/") and path.endswith("/jira-sync"):
                object_id = self.extract_object_id(path, suffix="/jira-sync")
                if object_id is None:
                    self.respond_html(not_found_page(), status=404)
                    return
                latest = conn.execute(
                    """
                    SELECT id
                    FROM object_versions
                    WHERE object_id = ?
                    ORDER BY version_no DESC
                    LIMIT 1
                    """,
                    (object_id,),
                ).fetchone()
                if not latest:
                    redirect(self, f"/objects/{object_id}?flash=" + quote("Ingen version finns att synka."))
                    return
                try:
                    issue = sync_version_from_jira(conn, latest["id"])
                    redirect(
                        self,
                        f"/objects/{object_id}?flash=" + quote(f"Jira-beslut synkades från {issue['issue_key']}."),
                    )
                except ValueError as exc:
                    redirect(self, f"/objects/{object_id}?flash=" + quote(str(exc)))
                return
        self.respond_html(not_found_page(), status=404)

    def extract_object_id(self, path, suffix=""):
        cleaned = path[len("/objects/") :]
        if suffix:
            cleaned = cleaned[: -len(suffix)]
        cleaned = cleaned.strip("/")
        if cleaned.isdigit():
            return int(cleaned)
        return None

    def respond_html(self, body, status=200):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        return


def main():
    init_db()
    port = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    server = ThreadingHTTPServer((HOST, port), RegistryHandler)
    print(f"Referensbeteckningsregister startat på http://{HOST}:{port}")
    print(f"Databasfil: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServern stoppades.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
