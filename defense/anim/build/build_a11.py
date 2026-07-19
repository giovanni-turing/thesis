#!/usr/bin/env python3
"""Inject the A11 payload into the template -> self-contained HTML."""
from pathlib import Path

HERE = Path(__file__).parent
data = (HERE / "../data/a11_data.json").read_text()
tpl = (HERE / "a11_template.html").read_text()
assert "/*__DATA__*/" in tpl
out = HERE / "../a11_llm_race.html"
out.write_text(tpl.replace("/*__DATA__*/", data, 1))
print(f"wrote {out.resolve()} ({out.stat().st_size/1e6:.2f} MB)")
