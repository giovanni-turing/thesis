#!/usr/bin/env python3
"""review-db — a minimal LOCAL MCP server exposing exactly ONE read-only tool.

Option A of the verification protocol (§9.1): reviewer agents get `db_query(sql)`
and nothing else. Read-only is enforced three independent ways:
  1. SQL validation      — must be a single SELECT/WITH; write keywords rejected.
  2. Connection is READ ONLY — PGOPTIONS forces default_transaction_read_only=on
                           + statement_timeout=15s + search_path=provenance,public.
  3. Row cap             — the query is wrapped so at most 1000 rows return.
No vault / e2b / postgres_execute / destructive tools exist in this server's surface.

Transport: MCP stdio (newline-delimited JSON-RPC 2.0). Backend: psql subprocess.
Password: env PGPASSWORD, else fetched once from the local `postgres` container.
"""
import json, sys, os, re, subprocess

HOST = os.environ.get("REVIEW_DB_HOST", "localhost")
PORT = os.environ.get("REVIEW_DB_PORT", "5433")
USER = os.environ.get("REVIEW_DB_USER", "picolo")   # read-scoped app role
DB   = os.environ.get("REVIEW_DB_NAME", "postgres")
ROW_CAP = 1000
STMT_TIMEOUT_MS = 15000

def _password():
    # secret never lives in this file: env PGPASSWORD, else a 0600 local pw file.
    pw = os.environ.get("PGPASSWORD")
    if pw:
        return pw
    for path in (os.path.expanduser("~/.config/review-db/pw"),
                 "/home/gio/tese/review/tools/.pw"):
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            pass
    return ""

PGPASSWORD = _password()

_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
_WRITE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|copy|call|do|merge|"
    r"vacuum|reindex|refresh|lock|comment|set|reset|begin|commit|rollback|savepoint|"
    r"prepare|execute|listen|notify|cluster|analyze|checkpoint|import|security)\b", re.I)

def validate(sql: str):
    s = _COMMENT.sub(" ", sql).strip().rstrip(";").strip()
    if not s:
        return None, "empty query"
    if ";" in s:
        return None, "multiple statements are not allowed (single SELECT only)"
    if s.split(None, 1)[0].lower() not in ("select", "with"):
        return None, "only SELECT / WITH queries are allowed"
    m = _WRITE.search(s)
    if m:
        return None, f"disallowed keyword '{m.group(0)}' — this tool is read-only (SELECT only)"
    return s, None

def run_query(sql: str):
    clean, err = validate(sql)
    if err:
        return {"error": err}
    wrapped = (f"SELECT coalesce(json_agg(_lim), '[]'::json) "
               f"FROM (SELECT * FROM ({clean}) _q LIMIT {ROW_CAP}) _lim;")
    env = dict(os.environ)
    env["PGPASSWORD"] = PGPASSWORD
    env["PGOPTIONS"] = (f"-c default_transaction_read_only=on "
                        f"-c statement_timeout={STMT_TIMEOUT_MS} "
                        f"-c search_path=provenance,public")
    try:
        r = subprocess.run(
            ["psql", "-h", HOST, "-p", PORT, "-U", USER, "-d", DB,
             "-v", "ON_ERROR_STOP=1", "--no-psqlrc", "-tAc", wrapped],
            capture_output=True, text=True, timeout=30, env=env)
    except subprocess.TimeoutExpired:
        return {"error": "query timed out (>30s wall / 15s statement)"}
    if r.returncode != 0:
        return {"error": (r.stderr or "query failed").strip()[:800]}
    try:
        rows = json.loads(r.stdout.strip() or "[]")
    except Exception:
        return {"error": "could not parse result", "raw": r.stdout[:400]}
    return {"rows": rows, "row_count": len(rows),
            "truncated": len(rows) >= ROW_CAP}

# ---- MCP stdio (newline-delimited JSON-RPC 2.0) ----
TOOL = {
    "name": "db_query",
    "description": ("Run ONE read-only SQL SELECT against the `provenance` database "
                    "(PostgreSQL, schema provenance, ~99M rows). Start at v_dim, filter "
                    "is_current. Returns up to 1000 rows as JSON. SELECT/WITH only."),
    "inputSchema": {"type": "object",
                    "properties": {"sql": {"type": "string", "description": "a single SELECT/WITH query"}},
                    "required": ["sql"]},
}

def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n"); sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        mid = req.get("id"); method = req.get("method")
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "review-db", "version": "1.0"}}})
        elif method == "notifications/initialized":
            pass  # notification, no reply
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [TOOL]}})
        elif method == "tools/call":
            params = req.get("params") or {}
            if params.get("name") != "db_query":
                send({"jsonrpc": "2.0", "id": mid,
                      "error": {"code": -32602, "message": "unknown tool"}})
                continue
            out = run_query((params.get("arguments") or {}).get("sql", ""))
            is_err = "error" in out
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": json.dumps(out)}],
                "isError": is_err}})
        elif mid is not None:
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32601, "message": f"method not found: {method}"}})

if __name__ == "__main__":
    main()
