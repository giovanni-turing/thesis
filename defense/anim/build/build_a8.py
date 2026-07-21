#!/usr/bin/env python3
"""A8 'The onset map' — assemble per-episode verdict data and emit the
self-contained page (defense/anim/a8_onset_map.html).

All 18 burst episodes (thesis Ch.3 definition; re-derived in
windows_ext.json) x reactive/forecast p99 per lead, from the verified run
sets (a2_runs, a2x_runs). burst2/6 reactive L<=45 reproduce thesis Tab 7.3;
L165 and e-cells are new runs under the identical law.
"""
import json
import re
from pathlib import Path

ROOT = Path("/home/gio/tese")
WINS = json.load(open(ROOT / "defense/anim/data/windows_ext.json"))
v = json.load(open(ROOT / "defense/anim/data/a2_runs/verification.json"))
v.update(json.load(open(ROOT / "defense/anim/data/a2x_runs/verification.json")))
LEADS = [15, 30, 45, 165]
ONSET_B = {"burst1": 220, "burst2": 48, "burst3": 1, "burst4": 60, "burst5": 35, "burst6": 1}
A2_LOADED = {"burst1", "burst3", "burst4", "burst5", "e10", "e11", "e13", "e17"}

eps = []
for key in [f"burst{i}" for i in range(1, 7)] + [f"e{i}" for i in range(7, 19)]:
    w = WINS[key]
    m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", w["note"])
    start = m.group(1) if m else "?"
    rec = {
        "key": key, "label": key.replace("burst", "b"),
        "start": start,
        "onset": ONSET_B.get(key, w.get("onset_min")),
        "peak": round(w["peak_1min_img_per_s"], 1),
        "requests": w["max_requests"],
        "coverage": w.get("in_coverage", key not in ("burst2", "burst6")),
        "a2": key in A2_LOADED,
        "re": {}, "fc": {},
    }
    if key in ("burst2", "burst6"):
        rec["coverage"] = False  # forecast-context days: no archived forecast
    for L in LEADS:
        r = v.get(f"{key}_reactive_L{L}")
        rec["re"][str(L)] = round(r["p99_ms"], 1) if r else None
        f = v.get(f"{key}_forecast_L{L}")
        rec["fc"][str(L)] = round(f["p99_ms"], 1) if f else None
    eps.append(rec)

DATA = {"sla": 1000.0, "leads": LEADS, "episodes": eps,
        "provenance": "verified runs: defense/anim/data/{a2_runs,a2x_runs}/verification.json; "
                      "burst1/3/4/5 + burst2/6 L<=45 reproduce ledgered cells (results_44.jsonl, "
                      "factorial_issuetime, thesis Tab 7.3); all other cells are new runs, identical law"}

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A8 — The onset map</title>
<style>
  :root { color-scheme: light;
    --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --muted:#898781;
    --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
    --blue:#2a78d6; --good:#0ca30c; --critical:#d03b3b; }
  * { box-sizing:border-box; margin:0; padding:0; }
  html,body { height:100%; }
  body { background:var(--page); color:var(--ink); overflow:hidden;
    font-family:system-ui,-apple-system,"Segoe UI",sans-serif; display:flex; flex-direction:column; }
  header { display:flex; align-items:center; gap:16px; padding:12px 24px 6px; }
  header h1 { font-size:21px; font-weight:650; }
  header .sub { font-size:12.5px; color:var(--ink-2); margin-top:2px; }
  .ctl { display:flex; align-items:center; gap:6px; margin-left:auto; }
  .ctl .lbl { font-size:10px; color:var(--muted); font-weight:600; letter-spacing:0.06em; text-align:right; line-height:1.2; }
  .seg { display:flex; border:1px solid var(--border); border-radius:9px; overflow:hidden; background:var(--surface); }
  .seg button { font:inherit; font-size:13px; font-weight:600; padding:6px 13px; border:0;
    background:transparent; cursor:pointer; color:var(--ink-2); }
  .seg button + button { border-left:1px solid var(--border); }
  .seg button.on { background:var(--ink); color:#fff; }
  #summary { padding:2px 24px 4px; font-size:13.5px; color:var(--ink-2); }
  #summary b { color:var(--ink); }
  #chartwrap { flex:1; margin:0 24px 6px; position:relative;
    background:var(--surface); border:1px solid var(--border); border-radius:14px; }
  canvas { position:absolute; inset:0; width:100%; height:100%; }
  footer { display:flex; gap:14px; align-items:center; padding:2px 24px 8px; font-size:10.5px; color:var(--muted); }
  footer .spacer { flex:1; }
  .lg { display:inline-flex; align-items:center; gap:5px; margin-right:12px; }
  .dotp { width:11px; height:11px; border-radius:50%; display:inline-block; }
  #tooltip { position:fixed; z-index:30; pointer-events:none; display:none;
    background:var(--ink); color:#fff; border-radius:8px; padding:8px 11px;
    font-size:12px; line-height:1.55; font-variant-numeric:tabular-nums;
    box-shadow:0 4px 16px rgba(0,0,0,0.3); }
  #tooltip table { border-collapse:collapse; margin-top:3px; }
  #tooltip td { padding:0 7px 0 0; }
  a.back { color:var(--blue); text-decoration:none; font-size:12px; }
</style>
</head>
<body>
<header>
  <div>
    <h1>The onset map — all 18 burst episodes</h1>
    <div class="sub">Each dot = one episode of the trace (Ch. 3 definition) · fill = reactive verdict at the chosen lead · ring = forecast (Chronos p90) verdict · click a dot to replay it in A2</div>
  </div>
  <div class="ctl">
    <span class="lbl">COLD-START<br>LEAD L</span>
    <div class="seg" id="leadSeg">
      <button data-l="15">15 s</button><button data-l="30" class="on">30 s</button>
      <button data-l="45">45 s</button><button data-l="165">165 s</button>
    </div>
  </div>
</header>
<div id="summary"></div>
<div id="chartwrap"><canvas id="cv"></canvas></div>
<footer>
  <span class="lg"><span class="dotp" style="background:var(--good)"></span>reactive passes</span>
  <span class="lg"><span class="dotp" style="background:var(--critical)"></span>reactive fails (p99 ≥ 1 s)</span>
  <span class="lg"><span class="dotp" style="border:2.5px solid var(--blue)"></span>forecast passes</span>
  <span class="lg"><span class="dotp" style="border:2.5px dashed var(--critical)"></span>forecast fails</span>
  <span class="lg"><span class="dotp" style="border:2px dashed var(--muted)"></span>no forecast (context days)</span>
  <span class="spacer"></span>
  <span>isolated ±10-min window replays, ρ=15 · ledgered cells reproduced exactly; others new runs, identical law</span>
  <a class="back" href="index.html">← launcher</a>
</footer>
<div id="tooltip"></div>
<script>
const DATA = /*__DATA__*/;
let lead = "30";
const cv = document.getElementById("cv"), ctx = cv.getContext("2d");
const wrap = document.getElementById("chartwrap");
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const PAD = { l: 64, r: 30, t: 26, b: 44 };
let W = 0, H = 0, pts = [];

const XMIN = 0.85, XMAX = 300;
const x = m => PAD.l + (Math.log10(m) - Math.log10(XMIN)) / (Math.log10(XMAX) - Math.log10(XMIN)) * (W - PAD.l - PAD.r);
const YMIN = 215, YMAX = 385;
const y = p => H - PAD.b - (p - YMIN) / (YMAX - YMIN) * (H - PAD.t - PAD.b);

function draw() {
  const dpr = devicePixelRatio || 1;
  const r = wrap.getBoundingClientRect();
  W = r.width; H = r.height;
  cv.width = W * dpr; cv.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  // grid + axes
  ctx.font = "11px system-ui"; ctx.fillStyle = css("--muted");
  for (const t of [1, 2, 5, 10, 30, 60, 120, 220]) {
    ctx.strokeStyle = css("--grid");
    ctx.beginPath(); ctx.moveTo(x(t), PAD.t); ctx.lineTo(x(t), H - PAD.b); ctx.stroke();
    ctx.textAlign = "center"; ctx.textBaseline = "top";
    ctx.fillText(t, x(t), H - PAD.b + 7);
  }
  for (let p = 225; p <= 375; p += 50) {
    ctx.strokeStyle = css("--grid");
    ctx.beginPath(); ctx.moveTo(PAD.l, y(p)); ctx.lineTo(W - PAD.r, y(p)); ctx.stroke();
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    ctx.fillText(p, PAD.l - 8, y(p));
  }
  ctx.strokeStyle = css("--axis");
  ctx.strokeRect(PAD.l, PAD.t, W - PAD.l - PAD.r, H - PAD.t - PAD.b);
  ctx.font = "600 12px system-ui"; ctx.fillStyle = css("--ink-2");
  ctx.textAlign = "center"; ctx.textBaseline = "bottom";
  ctx.fillText("onset: baseline → peak (minutes, log)", (PAD.l + W - PAD.r) / 2, H - 6);
  ctx.save(); ctx.translate(16, (PAD.t + H - PAD.b) / 2); ctx.rotate(-Math.PI / 2);
  ctx.textBaseline = "top"; ctx.fillText("episode peak (img/s, 1-min)", 0, 0); ctx.restore();
  // region hints
  ctx.font = "600 11.5px system-ui"; ctx.fillStyle = css("--muted");
  ctx.textAlign = "left"; ctx.textBaseline = "top";
  ctx.fillText("← fast onsets: reactive-dead zone", PAD.l + 10, PAD.t + 6);
  ctx.textAlign = "right";
  ctx.fillText("slow onsets: observable in time →", W - PAD.r - 10, PAD.t + 6);
  // dots
  pts = [];
  for (const [i, e] of DATA.episodes.entries()) {
    const jit = 1 + ((i * 2654435761 % 100) / 100 - 0.5) * 0.22;   // disclosed deterministic de-overlap
    const ex = x(Math.max(e.onset, 1) * jit), ey = y(e.peak);
    const rp = e.re[lead], fp = e.fc[lead];
    const reFail = rp !== null && rp >= DATA.sla;
    // forecast ring
    if (fp === null) { ctx.setLineDash([3, 3]); ctx.strokeStyle = css("--muted"); ctx.lineWidth = 2; }
    else if (fp >= DATA.sla) { ctx.setLineDash([4, 3]); ctx.strokeStyle = css("--critical"); ctx.lineWidth = 3; }
    else { ctx.setLineDash([]); ctx.strokeStyle = css("--blue"); ctx.lineWidth = 2.5; }
    ctx.beginPath(); ctx.arc(ex, ey, 13, 0, 6.2832); ctx.stroke(); ctx.setLineDash([]);
    // reactive fill
    ctx.fillStyle = rp === null ? css("--muted") : (reFail ? css("--critical") : css("--good"));
    ctx.beginPath(); ctx.arc(ex, ey, 8.5, 0, 6.2832); ctx.fill();
    // glyph (CVD-safe secondary encoding)
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 2;
    if (reFail) { ctx.beginPath(); ctx.moveTo(ex-3.5,ey-3.5); ctx.lineTo(ex+3.5,ey+3.5);
      ctx.moveTo(ex+3.5,ey-3.5); ctx.lineTo(ex-3.5,ey+3.5); ctx.stroke(); }
    else { ctx.beginPath(); ctx.moveTo(ex-3.5,ey+0.5); ctx.lineTo(ex-1,ey+3.5); ctx.lineTo(ex+3.5,ey-3); ctx.stroke(); }
    // label
    ctx.font = "700 11px system-ui"; ctx.textBaseline = "middle";
    ctx.strokeStyle = css("--surface"); ctx.lineWidth = 3;
    const side = i % 2 ? -1 : 1;
    ctx.textAlign = side > 0 ? "left" : "right";
    const lbl = e.label + (e.key === "e13" ? " ⚠" : "");
    ctx.strokeText(lbl, ex + 16 * side, ey);
    ctx.fillStyle = css("--ink-2"); ctx.fillText(lbl, ex + 16 * side, ey);
    pts.push({ ...e, ex, ey });
  }
  // summary
  const inplay = DATA.episodes.filter(e => e.re[lead] !== null);
  const rf = inplay.filter(e => e.re[lead] >= DATA.sla).length;
  const fmiss = DATA.episodes.filter(e => e.fc[lead] !== null && e.fc[lead] >= DATA.sla)
                             .map(e => e.label);
  const ff = fmiss.length;
  const ftxt = ff === 0 ? "none"
    : fmiss.join(", ") + (fmiss.length === 1 && fmiss[0] === "e13" ? " — the forecast-miss boundary case" : "");
  document.getElementById("summary").innerHTML =
    `At L = <b>${lead} s</b>: reactive fails <b>${rf} of ${inplay.length}</b> episodes · ` +
    `forecast fails <b>${ff}</b> (${ftxt}) · ` +
    `the dead zone grows with lead — drag it.`;
}
document.querySelectorAll("#leadSeg button").forEach(b => b.onclick = () => {
  lead = b.dataset.l;
  document.querySelectorAll("#leadSeg button").forEach(o => o.classList.toggle("on", o === b));
  draw();
});
const tt = document.getElementById("tooltip");
cv.addEventListener("mousemove", e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const hit = pts.find(p => (p.ex-mx)**2 + (p.ey-my)**2 < 170);
  cv.style.cursor = hit && hit.a2 ? "pointer" : "default";
  if (!hit) { tt.style.display = "none"; return; }
  const fmt = v => v === null ? "—" : (v >= 10000 ? (v/1000).toFixed(1)+" s" : v >= 1000 ? (v/1000).toFixed(2)+" s" : Math.round(v)+" ms");
  let rows = DATA.leads.map(L =>
    `<tr><td>L=${L}s</td><td style="color:${hit.re[L]>=DATA.sla?'#ff9d9d':'#9fe6a0'}">${fmt(hit.re[L])}</td>` +
    `<td style="color:${hit.fc[L]===null?'#bbb':hit.fc[L]>=DATA.sla?'#ff9d9d':'#9fe6a0'}">${fmt(hit.fc[L])}</td></tr>`).join("");
  tt.innerHTML = `<b>${hit.label}</b> · ${hit.start} UTC · peak ${hit.peak} img/s · onset ${hit.onset} min · ${hit.requests.toLocaleString("en-US")} req` +
    `<table><tr><td></td><td>reactive</td><td>forecast</td></tr>${rows}</table>` +
    (hit.coverage ? "" : "<div style='color:#bbb'>forecast-context days: no archived forecast</div>") +
    (hit.a2 ? "<div style='color:#9ec5f4'>click to replay in A2</div>" : "");
  tt.style.display = "block";
  tt.style.left = Math.min(e.clientX + 14, innerWidth - 300) + "px";
  tt.style.top = Math.min(e.clientY + 14, innerHeight - 170) + "px";
});
cv.addEventListener("mouseleave", () => tt.style.display = "none");
cv.addEventListener("click", e => {
  const r = cv.getBoundingClientRect();
  const hit = pts.find(p => (p.ex-(e.clientX-r.left))**2 + (p.ey-(e.clientY-r.top))**2 < 170);
  if (hit && hit.a2) location.href = `a2_the_race.html#w=${hit.key}&L=${lead === "165" ? "165" : lead}`;
});
addEventListener("resize", draw);
draw();
</script>
</body>
</html>
"""

out = ROOT / "defense/anim/a8_onset_map.html"
out.write_text(HTML.replace("/*__DATA__*/", json.dumps(DATA, separators=(",", ":")), 1))
print(f"wrote {out} ({out.stat().st_size/1e3:.0f} KB), {len(eps)} episodes")
