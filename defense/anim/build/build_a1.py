#!/usr/bin/env python3
"""Inject the extracted A1 payload into the template -> self-contained HTML."""
from pathlib import Path

HERE = Path(__file__).parent
data = (HERE / "../data/a1_data.json").read_text()
tpl = (HERE / "a1_template.html").read_text()
assert "/*__DATA__*/" in tpl
out = HERE / "../a1_invisible_failure.html"
out.write_text(tpl.replace("/*__DATA__*/", data, 1))
print(f"wrote {out.resolve()} ({out.stat().st_size/1e6:.2f} MB)")
