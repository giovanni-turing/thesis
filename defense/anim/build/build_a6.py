#!/usr/bin/env python3
"""Inject the A6 payload into the template -> self-contained HTML."""
from pathlib import Path

HERE = Path(__file__).parent
data = (HERE / "../data/a6_data.json").read_text()
tpl = (HERE / "a6_template.html").read_text()
assert "/*__DATA__*/" in tpl
out = HERE / "../a6_the_week.html"
out.write_text(tpl.replace("/*__DATA__*/", data, 1))
print(f"wrote {out.resolve()} ({out.stat().st_size/1e6:.2f} MB)")
