#!/usr/bin/env python3
"""Bridge protocol v1.8 linter + thread-state generator. Run from review/bridge/.
v1.3 (2026-07-26, threads D01/D02): re:-graph dispute-chain machine (one root
finding, linear, <=2 responses, escalation only after the 2nd response and
terminal); strict header grammar (no YAML claim); nonempty bounded values;
end-to-end qualified references; symlink-safe atomic STATE.md; the claude/003
threading defect is a DOCUMENTED EXCEPTION in BRIDGE.md, not an allowlist."""
import os, re, sys, glob, datetime, tempfile

TYPES = {"finding","question","response","rereview-request","ack","escalation","verification"}
SENDERS = {"claude","reviewer"}
LIVE_DIR_OWNER = {"to_reviewer":"claude","from_reviewer":"reviewer"}
HDR_KEYS = ["from","ts","re","type","thread","authority"]  # thread/authority optional
REQ_KEYS = ["from","ts","re","type"]
FNAME_RE = re.compile(r"^\d{3}_[A-Za-z0-9][A-Za-z0-9_-]*$")
THREAD_RE = re.compile(r"^D\d{2,}-[A-Za-z0-9][A-Za-z0-9_-]*$")
# v1.6 (D26): exact-identity exception -- message 033 predates the authority-header rule;
# its delegated authority is documented in BRIDGE.md and the session transcript.
ADJUDICATION_EXCEPTIONS = {"033_adjudication_d19_d22"}
GRANDFATHER_SHA = {"033_adjudication_d19_d22":
                   "c7c02dba550c1fd1ad9fe173ea5e005e0db62805de0b099c53903eba2e34ee01"}
# v1.8 (D35): authority values are BOUND to senders; rulings are expressed only
# through exact 'RULING <full-thread-id>: <verdict>' lines inside a valid
# unthreaded adjudication message. Mentions confer nothing.
AUTHORITY_SENDER = {"author": {"claude", "reviewer"},
                    "author-delegated:fable-5-2026-07-26": {"claude"},
                    "author-delegated:fable-5-2026-07-27-xhigh": {"claude"}}
RULING_RE = None
# v1.7 (D26 round 3): the only authorities this bridge recognizes. A heading-level
# adjudication with any other value is an error; STATE trusts only these.
VALID_AUTHORITIES = {"author", "author-delegated:fable-5-2026-07-26",
                     "author-delegated:fable-5-2026-07-27-xhigh"}
THREADED_TYPES = {"finding","response","escalation","verification"}

def parse_header(path, errs):
    lines = open(path).read().splitlines()
    if not lines or lines[0] != "---":
        errs.append(f"{path}: header must start with '---'"); return None
    hdr, i = {}, 1
    while i < len(lines) and lines[i] != "---":
        m = re.match(r"^([a-z]+):\s*(.*\S)\s*$", lines[i])
        if not m:
            errs.append(f"{path}: malformed or empty-valued header line {i+1}: {lines[i]!r}"); return None
        k, v = m.group(1), m.group(2)
        if k not in HDR_KEYS: errs.append(f"{path}: unknown header key '{k}'"); return None
        if k in hdr: errs.append(f"{path}: duplicate header key '{k}'"); return None
        hdr[k] = v; i += 1
    if i >= len(lines):
        errs.append(f"{path}: unterminated header"); return None
    for k in REQ_KEYS:
        if k not in hdr: errs.append(f"{path}: missing header '{k}'")
    return hdr

def live_lines(body):
    """Markdown-live lines. Fences: an opening run of >=3 backticks/tildes (up to 3
    leading spaces) with ANY info string opens; only a bare same-char run of >= the
    opening length closes. Excludes 4-space/tab-indented lines and HTML comments."""
    import re as _r
    body = _r.sub(r"<!--.*?-->", "", body, flags=_r.S)
    out, fence_char, fence_len = [], None, 0
    for raw in body.splitlines():
        if fence_char is None:
            fm = _r.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw)
            if fm and ("`" not in fm.group(2) if fm.group(1)[0] == "`" else True):
                fence_char, fence_len = fm.group(1)[0], len(fm.group(1))
                continue
        else:
            cm = _r.match(r"^ {0,3}(" + ("`" if fence_char == "`" else "~") + r"{3,})\s*$", raw)
            if cm and len(cm.group(1)) >= fence_len:
                fence_char, fence_len = None, 0
            continue
        if raw.startswith("    ") or raw.startswith("\t"):
            continue
        out.append(raw)
    return out

def is_adjudication_heading(ln):
    """Valid ATX heading (1-6 #, then a space) whose text is exactly AUTHOR ADJUDICATION."""
    import re as _r
    mm = _r.match(r"^ {0,3}(#{1,6}) (.*?)\s*#*\s*$", ln)
    return bool(mm) and mm.group(2).strip().upper() == "AUTHOR ADJUDICATION"

def threads_in_body(body):
    return set(re.findall(r"D\d{2,}-[A-Za-z0-9][A-Za-z0-9_-]*", body))

def valid_ts(s):
    try:
        return datetime.datetime.fromisoformat(s).utcoffset() is not None
    except Exception:
        return False

def main():
    msgs, errors = [], []
    seen_names = {}
    for d in ["to_reviewer","from_reviewer","archive"]:
        for p in sorted(glob.glob(f"{d}/*.md")):
            name = os.path.basename(p)[:-3]
            if name in seen_names:
                errors.append(f"{p}: duplicate basename (also in {seen_names[name]})")
            seen_names[name] = d
            if not FNAME_RE.match(name):
                errors.append(f"{p}: filename must be NNN_<nonempty-slug>.md")
            hdr = parse_header(p, errors) or {}
            _txt = open(p).read()
            body = _txt.split("---", 2)[2] if _txt.count("---") >= 2 else ""
            if hdr:
                if hdr.get("from") and hdr["from"] not in SENDERS:
                    errors.append(f"{p}: sender '{hdr['from']}' not in {sorted(SENDERS)}")
                if d in LIVE_DIR_OWNER and hdr.get("from") in SENDERS and hdr["from"] != LIVE_DIR_OWNER[d]:
                    errors.append(f"{p}: in {d}/ but from '{hdr['from']}' (owner: {LIVE_DIR_OWNER[d]})")
                if hdr.get("ts") and not valid_ts(hdr["ts"]):
                    errors.append(f"{p}: ts '{hdr['ts']}' not ISO-8601 with explicit UTC offset")
                if hdr.get("type") and hdr["type"] not in TYPES:
                    errors.append(f"{p}: bad type '{hdr['type']}'")
                if hdr.get("thread") is not None and not THREAD_RE.match(hdr.get("thread","")):
                    errors.append(f"{p}: thread id '{hdr.get('thread')}' not DNN-<slug>")
                if hdr.get("type") in ("finding","escalation") and "thread" not in hdr:
                    errors.append(f"{p}: type {hdr['type']} requires 'thread'")
            msgs.append({"file":name,"dir":d,"hdr":hdr,"body":body})
    by_name = {m["file"]: m for m in msgs}
    # re: resolution incl. end-to-end qualified form
    for m in msgs:
        r = m["hdr"].get("re","")
        if not r or r == "new": continue
        qual, target = (r.split(":",1)+[None])[:2] if ":" in r else (None, r)
        if qual is not None:
            if qual not in SENDERS:
                errors.append(f"{m['file']}: re qualifier '{qual}' not a valid sender"); continue
        if target not in by_name:
            errors.append(f"{m['file']}: re '{r}' not found"); continue
        tgt = by_name[target]
        if qual is not None and tgt["hdr"].get("from") != qual:
            errors.append(f"{m['file']}: re '{r}' qualifier does not match target sender '{tgt['hdr'].get('from')}'")
        tthread = tgt["hdr"].get("thread")
        if tthread and m["hdr"].get("thread") != tthread:
            errors.append(f"{m['file']}: replies to threaded '{target}' (thread {tthread}) "
                          f"but carries thread '{m['hdr'].get('thread')}'")
    # v1.6 (D26): verification semantics enforced globally, not only in chains.
    # v1.8: build the recognized-adjudication set FIRST (chain rules consult it)
    import hashlib as _hl
    adjudicated_threads = {}
    for m in sorted(msgs, key=lambda x: x["file"]):
        body = m.get("body", "")
        heading = any(is_adjudication_heading(ln) for ln in live_lines(body))
        if m["file"] in ADJUDICATION_EXCEPTIONS:
            import os as _os
            for d in ("to_reviewer", "from_reviewer", "archive"):
                fp = _os.path.join(d, m["file"] + ".md")
                if _os.path.exists(fp):
                    if _hl.sha256(open(fp, "rb").read()).hexdigest() != GRANDFATHER_SHA[m["file"]]:
                        errors.append(f"{m['file']}: grandfathered adjudication MUTATED (sha mismatch)")
                    break
            else:
                errors.append(f"{m['file']}: grandfathered file missing")
            for t in threads_in_body(body):
                adjudicated_threads.setdefault(t, (m["file"], "CLOSED-FIXED"))
            continue
        if not heading:
            continue
        auth = m["hdr"].get("authority")
        ok_auth = (auth in VALID_AUTHORITIES
                   and m["hdr"].get("from") in AUTHORITY_SENDER.get(auth, set())
                   and "thread" not in m["hdr"])
        if not ok_auth:
            continue  # header/registry errors are raised elsewhere
        n_rulings = 0
        for raw in live_lines(body):
            st = raw.strip()
            if re.match(r"^RULING[\W_]", st) or st == "RULING":
                mm = re.match(r"^RULING\s+(D\d{2,}-[A-Za-z0-9][A-Za-z0-9_-]*)\s*:\s*(CLOSED-FIXED|CLOSED-REJECTED|REOPENED)\s*$", st)
                if not mm:
                    errors.append(f"{m['file']}: malformed RULING line: {st[:60]!r}")
                    continue
                tkey, verdict = mm.group(1), mm.group(2)
                prev = adjudicated_threads.get(tkey)
                if prev is not None:
                    if prev[1] != verdict:
                        errors.append(f"{m['file']}: conflicting ruling for {tkey}: {verdict} vs {prev[1]} in {prev[0]}")
                    else:
                        errors.append(f"{m['file']}: duplicate ruling for {tkey} (already ruled in {prev[0]}) -- one ruling, one source")
                    continue
                n_rulings += 1
                adjudicated_threads[tkey] = (m["file"], verdict)
        if n_rulings == 0:
            errors.append(f"{m['file']}: asserted adjudication contains no valid RULING line")
    _all_thread_ids = {m["hdr"].get("thread") for m in msgs if m["hdr"].get("thread")}
    _escalated_ids = {m["hdr"].get("thread") for m in msgs
                      if m["hdr"].get("type") == "escalation" and m["hdr"].get("thread")}
    for t, (src, verdict) in list(adjudicated_threads.items()):
        if t not in _all_thread_ids:
            errors.append(f"{src}: RULING names unknown thread '{t}'")
        elif t not in _escalated_ids and src not in ADJUDICATION_EXCEPTIONS:
            errors.append(f"{src}: RULING for '{t}' which was never escalated")
    verif_names = {m["file"] for m in msgs if m["hdr"].get("type") == "verification"}
    for m in msgs:
        r = m["hdr"].get("re","")
        target = (r.split(":",1)[1] if ":" in r else r) if r else ""
        if target in verif_names:
            errors.append(f"{m['file']}: replies to verification '{target}' -- verifications are terminal, nothing may answer them")
        if m["hdr"].get("type") == "verification" and (not r or r == "new"):
            errors.append(f"{m['file']}: verification must name its exact target ('re: new' is invalid)")
        _asserts_adj = any(is_adjudication_heading(ln) for ln in live_lines(m.get("body","")))
        if _asserts_adj and m["file"] not in ADJUDICATION_EXCEPTIONS:
            if "authority" not in m["hdr"]:
                errors.append(f"{m['file']}: claims AUTHOR ADJUDICATION without an 'authority:' header")
            elif m["hdr"]["authority"] not in VALID_AUTHORITIES:
                errors.append(f"{m['file']}: authority '{m['hdr']['authority']}' not in the recognized registry")
            elif m["hdr"].get("from") not in AUTHORITY_SENDER.get(m["hdr"]["authority"], set()):
                errors.append(f"{m['file']}: authority '{m['hdr']['authority']}' not valid for sender '{m['hdr'].get('from')}'")
            elif "thread" in m["hdr"]:
                errors.append(f"{m['file']}: adjudications must be unthreaded")
    # sequences per sender: start 001, contiguous, no duplicates
    for who in SENDERS:
        seqs = sorted(int(m["file"][:3]) for m in msgs
                      if m["hdr"].get("from")==who and re.match(r"^\d{3}_", m["file"]))
        if seqs and seqs[0] != 1: errors.append(f"{who}: sequence starts at {seqs[0]:03d}, not 001")
        for a,b in zip(seqs, seqs[1:]):
            if b == a: errors.append(f"{who}: duplicate sequence number {a:03d}")
            elif b != a+1: errors.append(f"{who}: sequence gap {a:03d} -> {b:03d}")
    # dispute-chain machine: built from the re: graph, timestamps are metadata only
    threads = {}
    for m in msgs:
        t = m["hdr"].get("thread")
        if t: threads.setdefault(t, []).append(m)
    thread_state = {}
    for t, ms in threads.items():
        bad = False
        for m in ms:
            if m["hdr"].get("type") not in THREADED_TYPES:
                errors.append(f"thread {t}: {m['file']} has non-dispute type '{m['hdr'].get('type')}'"); bad = True
        roots = [m for m in ms if m["hdr"].get("type")=="finding"]
        if len(roots) != 1:
            errors.append(f"thread {t}: expected exactly one root finding, found {len(roots)}"); bad = True
        member = {m["file"] for m in ms}
        succ = {}
        for m in ms:
            r = m["hdr"].get("re",""); target = r.split(":",1)[1] if ":" in r else r
            if m["hdr"].get("type") == "finding":
                if target in member:
                    errors.append(f"thread {t}: root finding {m['file']} must not reply into its own thread"); bad = True
            else:
                if target not in member:
                    errors.append(f"thread {t}: {m['file']} must reply to a thread member (re: {r})"); bad = True
                elif target in succ:
                    errors.append(f"thread {t}: branch — both {succ[target]} and {m['file']} reply to {target}"); bad = True
                else: succ[target] = m["file"]
        if not bad and roots:
            chain, cur, seen = [roots[0]["file"]], roots[0]["file"], set()
            while cur in succ:
                if cur in seen: errors.append(f"thread {t}: cycle detected"); bad = True; break
                seen.add(cur); cur = succ[cur]; chain.append(cur)
            if not bad and len(chain) != len(ms):
                errors.append(f"thread {t}: disconnected messages (chain {len(chain)} of {len(ms)})"); bad = True
            if not bad:
                types = [by_name[n]["hdr"].get("type") for n in chain]
                root_from = by_name[chain[0]]["hdr"].get("from")
                other = ({"claude","reviewer"} - {root_from}).pop() if root_from in ("claude","reviewer") else None
                for i, ty in enumerate(types[1:], 1):
                    if ty == "verification":
                        if i != len(types)-1:
                            errors.append(f"thread {t}: verification {chain[i]} must be terminal"); bad=True
                        vfrom = by_name[chain[i]]["hdr"].get("from")
                        ffrom = by_name[chain[0]]["hdr"].get("from")
                        if vfrom != ffrom:
                            errors.append(f"thread {t}: terminal verification by '{vfrom}' -- only the finding's author ('{ffrom}') may attest its resolution"); bad=True
                        prev = types[i-1]
                        nresp_before = types[1:i].count("response")
                        _adj = adjudicated_threads.get(t)
                        if prev == "escalation" and (_adj is None or _adj[1] == "REOPENED"):
                            errors.append(f"thread {t}: post-escalation verification requires a recognized CLOSED ruling (none or REOPENED)"); bad=True
                        if not (prev == "escalation" or nresp_before >= 2):
                            errors.append(f"thread {t}: verification {chain[i]} only permitted after the second response or an escalation"); bad=True
                        continue
                    if ty == "response":
                        if i > 2: errors.append(f"thread {t}: third response {chain[i]} exceeds the two-round ceiling"); bad=True
                        want = other if i == 1 else root_from
                        got = by_name[chain[i]]["hdr"].get("from")
                        if want and got != want:
                            errors.append(f"thread {t}: response {i} ({chain[i]}) authored by '{got}', "
                                          f"alternation requires '{want}'"); bad=True
                    elif ty == "escalation":
                        if i != 3: errors.append(f"thread {t}: escalation {chain[i]} only permitted after the second response"); bad=True
                        if i != len(types)-1 and types[i+1] != "verification":
                            errors.append(f"thread {t}: escalation must be terminal (or followed only by a single verification)"); bad=True
                    else:
                        errors.append(f"thread {t}: type '{ty}' invalid inside a chain"); bad = True
                thread_state[t] = (chain, types)
    # STATE.md: symlink-safe, atomic
    if os.path.islink("STATE.md"):
        errors.append("STATE.md is a symlink — refusing to write"); state_ok = False
    else: state_ok = True
    out = [f"# Bridge state (generated {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}, protocol v1.8)\n",
           f"\nmessages: {len(msgs)}  errors: {len(errors)}\n", "\n## Dispute threads\n"]
    if not threads: out.append("(none)\n")
    for t in sorted(threads):
        if t in thread_state:
            chain, types = thread_state[t]
            nresp = types.count("response"); esc = "escalation" in types
            _adj = adjudicated_threads.get(t)
            adjudicated = esc and _adj is not None and _adj[1] != "REOPENED"
            reopened = esc and _adj is not None and _adj[1] == "REOPENED"
            tag = (f", ADJUDICATED {_adj[1]} (ruling in {_adj[0]})" if adjudicated else (f", REOPENED by author (ruling in {_adj[0]})" if reopened else (", ESCALATED - awaiting author" if esc else "")))
            out.append(f"- **{t}**: {len(chain)} msgs, {nresp}/2 evidence rounds{tag}\n")
            for n in chain: out.append(f"    - {n} ({by_name[n]['hdr'].get('from')}, {by_name[n]['hdr'].get('type')})\n")
        else:
            out.append(f"- **{t}**: INVALID CHAIN (see errors)\n")
    unv=[m for m in msgs if m["hdr"].get("type")=="verification" and not m["hdr"].get("thread")]
    if unv:
        out.append("\n## Unthreaded verifications (terminal attestations)\n")
        for m in unv: out.append(f"- {m['file']} ({m['hdr'].get('from')}) re: {m['hdr'].get('re')}\n")
    if errors: out.append("\n## Protocol errors\n" + "".join(f"- {e}\n" for e in errors))
    if state_ok:
        fd, tmp = tempfile.mkstemp(dir=".", prefix=".state.", suffix=".tmp")
        with os.fdopen(fd, "w") as f: f.write("".join(out))
        os.replace(tmp, "STATE.md")
    print(f"messages={len(msgs)} errors={len(errors)}")
    for e in errors: print("ERROR:", e)
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
