#!/usr/bin/env python3
"""Inject data + inline plotly into the A9 template -> self-contained HTML."""
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path("/home/gio/tese")
plotly = (ROOT / "eda/.venv/lib/python3.14/site-packages/plotly/package_data/plotly.min.js").read_text()
data = (HERE / "../data/a9_data.json").read_text()
tpl = (HERE / "a9_template.html").read_text()
assert "/*__PLOTLY__*/" in tpl and "/*__DATA__*/" in tpl
out = HERE / "../a9_dataset_kde.html"
out.write_text(tpl.replace("/*__PLOTLY__*/", plotly, 1).replace("/*__DATA__*/", data, 1))
print(f"wrote {out.resolve()} ({out.stat().st_size/1e6:.2f} MB)")
