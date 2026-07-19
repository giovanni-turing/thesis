#!/usr/bin/env python3
"""Inject the A2 payload into the template -> self-contained HTML."""
from pathlib import Path

HERE = Path(__file__).parent
data = (HERE / "../data/a2_data.json").read_text()
tpl = (HERE / "a2_template.html").read_text()
assert "/*__DATA__*/" in tpl
out = HERE / "../a2_the_race.html"
out.write_text(tpl.replace("/*__DATA__*/", data, 1))
print(f"wrote {out.resolve()} ({out.stat().st_size/1e6:.2f} MB)")
