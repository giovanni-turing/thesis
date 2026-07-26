#!/usr/bin/env python3
"""Bundle the reveal defense deck into ONE self-contained HTML file.

Inlines: vendor CSS (reset/reveal/theme), vendor JS (reveal, notes, plotly),
assets (week/method data, SVG logos as data: URIs), and the five animation
pages. Anim iframes become lazy Blob-URL iframes hydrated within distance 1
of the current slide and dehydrated beyond distance 2 (replicating reveal's
data-src viewDistance behavior, hash fragments preserved).

Output: defense/deck_single.html — works from file://.
"""
import base64
import json
import re
from pathlib import Path

HERE = Path(__file__).parent            # defense/reveal
ANIM = HERE.parent / "anim"
OUT = HERE.parent / "deck_single.html"

html = (HERE / "index.html").read_text()

# ---- vendor CSS -> inline <style> (strip the font @import; deck forces system-ui)
for css in ["vendor/dist/reset.css", "vendor/dist/reveal.css", "vendor/dist/theme/white.css"]:
    body = (HERE / css).read_text()
    body = re.sub(r'@import url\([^)]*\);', '', body)
    tag = f'<link rel="stylesheet" href="{css}">'
    assert tag in html, tag
    html = html.replace(tag, f"<style>/* inlined {css} */\n{body}\n</style>")

# ---- SVG logos -> data: URIs
for svg in ["assets/holysee.svg", "assets/usp.svg", "assets/ime.svg"]:
    b64 = base64.b64encode((HERE / svg).read_bytes()).decode()
    assert f'src="{svg}"' in html
    html = html.replace(f'src="{svg}"', f'src="data:image/svg+xml;base64,{b64}"')

# ---- vendor + asset JS -> inline <script>. The HTML parser ends a script
# block on `</script`, and `<!--` / `<script` shift it into escaped states that
# also break early; inside JS string literals `<\/`, `<\s`, `<\!` have identical
# values, so this escape is semantics-preserving for string content.
def script_safe(s: str) -> str:
    s = re.sub(r'</script', r'<\\/script', s, flags=re.I)
    s = re.sub(r'<script', r'<\\script', s, flags=re.I)
    s = s.replace('<!--', '<\\!--')
    return s

for js in ["vendor/dist/reveal.js", "vendor/plugin/notes/notes.js",
           "vendor/plotly.min.js", "assets/week_data.js"]:
    tag = f'<script src="{js}"></script>'
    assert tag in html, tag
    html = html.replace(tag, f"<script>/* inlined {js} */\n"
                        f"{script_safe((HERE / js).read_text())}\n</script>")
# method_data carries a cache-bust query
tag = '<script src="assets/method_data.js?v=5s"></script>'
assert tag in html
html = html.replace(tag, "<script>/* inlined assets/method_data.js */\n"
                    + script_safe((HERE / 'assets/method_data.js').read_text()) + "\n</script>")

# ---- anim iframes -> data-animkey placeholders + embedded page strings
anims = {}
def swap_iframe(m: re.Match) -> str:
    src = m.group(1)
    path, _, frag = src.partition("#")
    key = Path(path).stem
    anims[key] = (ANIM / Path(path).name).read_text()
    frag_attr = f' data-animfrag="#{frag}"' if frag else ""
    return f'<iframe class="r-stretch" data-animkey="{key}"{frag_attr} allow="fullscreen"></iframe>'

html, n = re.subn(r'<iframe class="r-stretch" data-src="\.\./anim/([^"]+)" allow="fullscreen"></iframe>',
                  swap_iframe, html)
assert n == 5, f"expected 5 anim iframes, swapped {n}"

# ---- loader: JSON-encoded pages -> Blob URLs, hydrate cur±1 / dehydrate >2
pages_js = "const ANIM_PAGES = {\n" + ",\n".join(
    f'"{k}": {script_safe(json.dumps(v))}' for k, v in anims.items()) + "\n};"
loader = """
<script>
/* ---- single-file anim loader: Blob-URL iframes, reveal-like lazy hydration ---- */
%s
const _animURL = {};
function animSrc(key) {
  if (!_animURL[key]) _animURL[key] = URL.createObjectURL(
    new Blob([ANIM_PAGES[key]], { type: "text/html" }));
  return _animURL[key];
}
function updateAnims() {
  const cur = Reveal.getIndices().h;
  document.querySelectorAll("iframe[data-animkey]").forEach(f => {
    const idx = Reveal.getIndices(f.closest("section")).h;
    const d = Math.abs(idx - cur);
    if (d <= 1 && !f.getAttribute("src"))
      f.src = animSrc(f.dataset.animkey) + (f.dataset.animfrag || "");
    else if (d > 2 && f.getAttribute("src")) f.removeAttribute("src");
  });
}
</script>
""" % pages_js
# splice BEFORE the Reveal.initialize script (must be parsed before its .then
# callback references updateAnims); rindex also dodges the literal "</body>"
# inside notes.js's speaker template
anchor = "<script>\n  Reveal.initialize({"
idx = html.rindex(anchor)
html = html[:idx] + loader + html[idx:]

# hook the loader into reveal's lifecycle (initialize .then already draws charts)
old = "}).then(drawWeekCharts);"
assert old in html
html = html.replace(old,
    "}).then(() => { drawWeekCharts(); updateAnims();\n"
    "    Reveal.on('slidechanged', updateAnims); });")

OUT.write_text(html)
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB, {len(anims)} anims embedded: {sorted(anims)})")
