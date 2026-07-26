import sys, json, subprocess, importlib.util
spec=importlib.util.spec_from_file_location("rdb","/home/gio/tese/review/tools/review_db_mcp.py")
rdb=importlib.util.module_from_spec(spec); spec.loader.exec_module(rdb)

def show(label, out):
    if "error" in out: print(f"  {label:38} -> ERROR: {out['error'][:70]}")
    else: print(f"  {label:38} -> rows={out['row_count']} trunc={out['truncated']} sample={json.dumps(out['rows'][:1])[:70]}")

print("=== A) legit read-only queries (should WORK) ===")
show("count current runs", rdb.run_query("SELECT count(*) AS c FROM provenance.v_dim WHERE is_current"))
show("latency view sample", rdb.run_query("SELECT window_name, p99_ms FROM provenance.v_pool_latency LIMIT 3"))
show("WITH cte", rdb.run_query("WITH x AS (SELECT 1 AS n) SELECT n*2 AS d FROM x"))

print("=== B) writes / DDL (should be REJECTED) ===")
for q in ["INSERT INTO provenance.runs VALUES (1)",
          "UPDATE provenance.runs SET pool='x'",
          "DELETE FROM provenance.runs",
          "DROP TABLE provenance.runs",
          "TRUNCATE provenance.runs",
          "SELECT 1; DELETE FROM provenance.runs",
          "WITH d AS (DELETE FROM provenance.runs RETURNING 1) SELECT * FROM d",
          "GRANT ALL ON provenance.runs TO public",
          "COPY provenance.runs TO '/tmp/x'"]:
    show(q[:38], rdb.run_query(q))

print("=== C) LIMIT cap (runs has 3147 rows -> should truncate to 1000) ===")
show("SELECT * FROM runs", rdb.run_query("SELECT * FROM provenance.runs"))

print("=== D) statement_timeout (pg_sleep 20s vs 15s cap -> ERROR) ===")
show("pg_sleep(20)", rdb.run_query("SELECT pg_sleep(20)"))

print("=== E) MCP stdio protocol handshake ===")
p=subprocess.Popen(["/usr/bin/python3","/home/gio/tese/review/tools/review_db_mcp.py"],
                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def rpc(obj):
    p.stdin.write(json.dumps(obj)+"\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
init=rpc({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}})
print("  initialize ->", init["result"]["serverInfo"])
p.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"})+"\n"); p.stdin.flush()
tl=rpc({"jsonrpc":"2.0","id":2,"method":"tools/list"})
print("  tools/list ->", [t["name"] for t in tl["result"]["tools"]])
tc=rpc({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"db_query","arguments":{"sql":"SELECT count(*) AS c FROM provenance.v_dim WHERE is_current"}}})
print("  tools/call db_query ->", tc["result"]["content"][0]["text"][:80], "isError=",tc["result"]["isError"])
p.stdin.close(); p.wait(timeout=5)
