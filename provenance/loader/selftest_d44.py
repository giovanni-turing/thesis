"""D44 closure proof: corrupt / settled-corruption / generator-failure each make
zero K16 DB calls. db.run_sql is monkeypatched with a counter; the tracked
artifact is mutated on disk and restored byte-identically afterwards."""
import hashlib, json, os, shutil, sys

sys.path.insert(0, "/home/gio/tese/provenance/loader")
os.chdir("/home/gio/tese/provenance/loader")
import db, loaders

PATH = "/home/gio/tese/simulation/results/composed_fill/composed_fill_joined.json"
ORIG = open(PATH, "rb").read()
JOIN = "/home/gio/tese/simulation/composed_fill_join.py"

calls = []
db.run_sql = lambda sql: calls.append(sql)

def expect_raise(label, idx, reload):
    calls.clear()
    try:
        loaders.load_composed_e2e_fill(idx, reload)
    except (AssertionError, FileNotFoundError) as e:
        print(f"{label}: RAISED ({type(e).__name__}: {str(e)[:80]}) db_calls={len(calls)}")
        return len(calls) == 0
    print(f"{label}: FAILED TO RAISE db_calls={len(calls)}")
    return False

ok = True
try:
    # 1. Corrupt artifact, fresh SHA (not in index)
    bad = ORIG.replace(b'"e2e_p99"', b'"e2e_p99_TAMPERED"', 1)
    assert bad != ORIG
    open(PATH, "wb").write(bad)
    ok &= expect_raise("corrupt-fresh", {}, True)

    # 2. Settled corruption: corrupt SHA already in index, reload=False.
    #    Guard must run BEFORE sha-skip -> raise, not silent (0,0).
    bad_sha = hashlib.sha256(bad).hexdigest()
    ok &= expect_raise("settled-corruption", {PATH: bad_sha}, False)

    # 3. Generator failure: clean bytes on disk, join script unavailable -> rc!=0
    open(PATH, "wb").write(ORIG)
    shutil.move(JOIN, JOIN + ".d44bak")
    try:
        ok &= expect_raise("generator-failure", {}, True)
    finally:
        shutil.move(JOIN + ".d44bak", JOIN)

    # 4. Clean path control: same monkeypatched counter, clean bytes -> writes happen
    calls.clear()
    n = loaders.load_composed_e2e_fill({}, True)
    print(f"clean-control: rows={n} db_calls={len(calls)} (>0 expected)")
    ok &= len(calls) > 0
finally:
    open(PATH, "wb").write(ORIG)
    restored = open(PATH, "rb").read() == ORIG
    print(f"artifact-restored-byte-identical: {restored}")
    ok &= restored

print("D44-NEGATIVE-TESTS:", "ALL PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
