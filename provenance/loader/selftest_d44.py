"""D44/D46/D47 regression suite for K16 -- D48-ISOLATED.

Every mutation happens inside a TemporaryDirectory holding a COPY of the
tracked artifact; `loaders.SIM` is patched to that tree, so K16 never reads
the repository artifact. The generator is MOCKED by patching subprocess.run
(success writes chosen bytes to --out; failure returns rc!=0; swap variants
mutate the copied artifact) -- the real join script is never renamed, written,
or executed except by one read-only integration control whose --out is a temp
child. db.run_sql is intercepted throughout. On exit the suite asserts the
repository artifact and generator are byte-identical to their startup
snapshots; no test path writes or renames either canonical file.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile

sys.path.insert(0, "/home/gio/tese/provenance/loader")
os.chdir("/home/gio/tese/provenance/loader")
import db, ingest_common, loaders

REPO_ARTIFACT = "/home/gio/tese/simulation/results/composed_fill/composed_fill_joined.json"
REPO_GENERATOR = "/home/gio/tese/simulation/composed_fill_join.py"
CANON_ART = open(REPO_ARTIFACT, "rb").read()
CANON_GEN = open(REPO_GENERATOR, "rb").read()

calls = []
db.run_sql = lambda sql: calls.append(sql)

real_run = subprocess.run
real_wt = ingest_common.is_worktree
real_loads = json.loads
real_SIM = loaders.SIM

gen_calls = []


class _R:
    returncode = 0
    stdout = stderr = ""


def mock_generator(bytes_out=None, rc=0, side=None):
    """Fake join script: counts invocations, writes bytes_out to --out on
    success, optionally runs a side effect (e.g. swap the copied artifact)."""
    def fake(cmd, **kw):
        gen_calls.append(cmd)
        if side:
            side()
        r = _R()
        r.returncode = rc
        if rc == 0 and bytes_out is not None:
            open(cmd[cmd.index("--out") + 1], "wb").write(bytes_out)
        return r
    return fake


ok = True
try:
    with tempfile.TemporaryDirectory(prefix="d48_iso_") as TD:
        SIM_ISO = os.path.join(TD, "results")
        os.makedirs(os.path.join(SIM_ISO, "composed_fill"))
        PATH = os.path.join(SIM_ISO, "composed_fill", "composed_fill_joined.json")
        ORIG = CANON_ART

        loaders.SIM = SIM_ISO
        ingest_common.is_worktree = lambda p: False   # deterministic; probe 5 overrides

        def reset():
            open(PATH, "wb").write(ORIG)

        def expect_raise(label, idx, reload):
            calls.clear()
            try:
                loaders.load_composed_e2e_fill(idx, reload)
            except (AssertionError, FileNotFoundError) as e:
                print(f"{label}: RAISED ({type(e).__name__}: {str(e)[:80]}) db_calls={len(calls)}")
                return len(calls) == 0
            print(f"{label}: FAILED TO RAISE db_calls={len(calls)}")
            return False

        # 1. Corrupt copied artifact, fresh SHA; regeneration (mock) is canonical.
        reset()
        bad = ORIG.replace(b'"e2e_p99"', b'"e2e_p99_TAMPERED"', 1)
        assert bad != ORIG
        open(PATH, "wb").write(bad)
        subprocess.run = mock_generator(bytes_out=ORIG)
        ok &= expect_raise("corrupt-fresh", {}, True)

        # 2. Settled corruption: corrupt sha PRE-SEEDED in the index, reload=False.
        bad_sha = hashlib.sha256(bad).hexdigest()
        ok &= expect_raise("settled-corruption", {PATH: bad_sha}, False)

        # 3. Generator failure (mock rc=2), clean copied bytes.
        reset()
        subprocess.run = mock_generator(rc=2)
        ok &= expect_raise("generator-failure", {}, True)

        # 4. Clean control: mock emits canonical bytes -> (1,9), one transaction.
        reset()
        subprocess.run = mock_generator(bytes_out=ORIG)
        calls.clear()
        n = loaders.load_composed_e2e_fill({}, True)
        print(f"clean-control: rows={n} db_calls={len(calls)} (>0 expected)")
        ok &= n == (1, 9) and len(calls) == 1

        # 5. Exclusion honored FIRST: corrupt excluded copy -> (0,0), zero
        #    generator and DB calls, before any read/regeneration.
        open(PATH, "wb").write(bad)
        ingest_common.is_worktree = lambda p: True
        gen_calls.clear()
        calls.clear()
        n = loaders.load_composed_e2e_fill({}, True)
        print(f"excluded-corrupt-path: ret={n} generator_calls={len(gen_calls)} db_calls={len(calls)}")
        ok &= n == (0, 0) and len(gen_calls) == 0 and len(calls) == 0
        ingest_common.is_worktree = lambda p: False

        # 6. Parse-time mutation: copy swapped during json parse -> final
        #    pre-DB freshness check refuses.
        reset()
        subprocess.run = mock_generator(bytes_out=ORIG)

        def _swapping_loads(s, *a, **kw):
            json.loads = real_loads
            open(PATH, "wb").write(ORIG + b"\n")
            return real_loads(s, *a, **kw)

        json.loads = _swapping_loads
        try:
            ok &= expect_raise("mid-run-swap-freshness", {}, True)
        finally:
            json.loads = real_loads

        # 7. D47: settled-skip freshness. Canonical sha pre-seeded, reload=False;
        #    the mock generator emits canonical --out bytes but swaps the copied
        #    artifact -> the SKIP branch must refuse, not attest (0,0).
        reset()
        canon_sha = hashlib.sha256(ORIG).hexdigest()
        subprocess.run = mock_generator(bytes_out=ORIG,
                                        side=lambda: open(PATH, "wb").write(b"{}"))
        ok &= expect_raise("settled-skip-freshness", {PATH: canon_sha}, False)

        # 7b. Clean settled control: untouched copy, guard runs, then (0,0) skip.
        reset()
        subprocess.run = mock_generator(bytes_out=ORIG)
        gen_calls.clear()
        calls.clear()
        n = loaders.load_composed_e2e_fill({PATH: canon_sha}, False)
        print(f"settled-clean-skip: ret={n} generator_calls={len(gen_calls)} db_calls={len(calls)}")
        ok &= n == (0, 0) and len(gen_calls) == 1 and len(calls) == 0

        # 8. Tempdir hygiene: no k16_regen_* leftovers from any probe above.
        left = [d for d in os.listdir(tempfile.gettempdir()) if d.startswith("k16_regen_")]
        print(f"tempdir-hygiene: leftovers={len(left)}")
        ok &= not left

        # 9. Integration control (READ-ONLY on canonical files): the REAL
        #    generator, run with a temp-child --out, reproduces the repository
        #    artifact byte-identically. Validates the mock's premise.
        _out = os.path.join(TD, "integration_regen.json")
        r = real_run(["/home/gio/tese/eda/.venv/bin/python", REPO_GENERATOR, "--out", _out],
                     capture_output=True, text=True, cwd="/home/gio/tese")
        ident = r.returncode == 0 and open(_out, "rb").read() == CANON_ART
        print(f"real-generator-integration: rc={r.returncode} byte_identical={ident}")
        ok &= ident
finally:
    subprocess.run = real_run
    ingest_common.is_worktree = real_wt
    json.loads = real_loads
    loaders.SIM = real_SIM

# 10. Canonical shared-tree files untouched -- the suite's isolation contract.
art_ok = open(REPO_ARTIFACT, "rb").read() == CANON_ART
gen_ok = open(REPO_GENERATOR, "rb").read() == CANON_GEN
print(f"canonical-artifact-unchanged: {art_ok}")
print(f"canonical-generator-unchanged: {gen_ok}")
ok &= art_ok and gen_ok

print("D44-NEGATIVE-TESTS:", "ALL PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
