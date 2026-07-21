"""Postgres transport for the provenance loader.

No psycopg needed: we shell out to the host `psql` (16.14) which reaches the ssd2
container at localhost:5433. Bulk load streams CSV into `psql \\copy ... FROM STDIN`
(COPY is COPY regardless of driver). Password is read from the container env at runtime
and never persisted.
"""
import os, subprocess, csv, functools

PGHOST, PGPORT, PGUSER, PGDATABASE = "localhost", "5433", "goku", "postgres"


@functools.lru_cache(maxsize=1)
def _password():
    # Source order: env override > credentials file (post-rotation) > container env (init-only, stale after ALTER ROLE)
    if os.environ.get("POSTGRES_PASSWORD"):
        return os.environ["POSTGRES_PASSWORD"]
    cred = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".goku_credentials")
    if os.path.exists(cred):
        for line in open(cred):
            if "password=" in line:
                return line.rsplit("password=", 1)[1].strip()
    r = subprocess.run(
        ["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", "postgres"],
        capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            return line.split("=", 1)[1]
    raise RuntimeError("POSTGRES_PASSWORD not found in env, credentials file, or `docker inspect postgres`")


@functools.lru_cache(maxsize=1)
def pgenv():
    e = dict(os.environ)
    e.update(PGHOST=PGHOST, PGPORT=PGPORT, PGUSER=PGUSER, PGDATABASE=PGDATABASE,
             PGPASSWORD=_password())
    return e


PSQL = ["psql", "-w", "-q", "-v", "ON_ERROR_STOP=1"]


def run_sql(sql):
    """Execute one or more `;`-separated statements (one connection).

    SQL is fed via stdin (`-f -`) not `-c`, so multi-row INSERTs are not bounded by ARG_MAX.
    """
    r = subprocess.run(PSQL + ["-f", "-"], input=sql, env=pgenv(), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr.strip()}\n--- SQL (first 400) ---\n{sql[:400]}")
    return r.stdout


def scalar(sql):
    r = subprocess.run(PSQL + ["-tAc", sql], env=pgenv(), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr.strip()}\nSQL: {sql[:200]}")
    return r.stdout.strip()


def rows(sql):
    """Return list of tuples (tab-separated, unaligned)."""
    r = subprocess.run(PSQL + ["-tAF\t", "-c", sql], env=pgenv(), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr.strip()}\nSQL: {sql[:200]}")
    return [tuple(line.split("\t")) for line in r.stdout.splitlines() if line]


def _cell(v):
    if v is None:
        return ""
    if v is True:
        return "t"
    if v is False:
        return "f"
    if isinstance(v, (list, tuple)):
        return "{" + ",".join("" if x is None else str(x) for x in v) + "}"
    return v  # int/float/str -> csv.writer will str() it


def copy_rows(table, columns, row_iter):
    """Stream rows into provenance.<table> via psql \\copy CSV. Returns row count.

    row_iter yields tuples aligned to `columns`. None->NULL, bool->t/f, list->{a,b,c}.
    """
    cols = ",".join(columns)
    cmd = f"\\copy provenance.{table} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '')"
    proc = subprocess.Popen(PSQL + ["-c", cmd], env=pgenv(),
                            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True)
    w = csv.writer(proc.stdin)
    n = 0
    try:
        for row in row_iter:
            w.writerow([_cell(v) for v in row])
            n += 1
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
    err = proc.stderr.read()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"copy into {table} failed: {err.strip()}")
    return n
