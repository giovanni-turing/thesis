# Visual review mailbox (parallel to review/bridge)

Scope: VISUAL artifacts only — deck slides (defense/reveal/index.html +
defense/deck_single.html mirror), thesis figures (figuras/**), rendered PDF
pages (tables/floats/margins/collisions), defense-qa.pdf layout. Scientific
claims, numbers, and prose semantics belong to review/bridge, NOT here; a
visual finding that implies a content change must be cross-referenced to a
bridge thread instead of ruled on here.

Message format: identical to review/bridge (frontmatter from/ts/re/type,
threads VNN-<slug> for findings), validated by ./validate.py run inside this
directory. Senders: claude (editor) and reviewer.

Artifact map for the reviewer:
- Deck source: defense/reveal/index.html  (rebuild: cd defense/reveal &&
  python3 build_single_deck.py — must report 5 anims embedded)
- Packed mirror: defense/deck_single.html (byte-consistency with source is
  gated by verification/metric_stack_gate.py for bound tiles)
- Slide screenshots: chromium --headless --disable-gpu
  --window-size=1920,1080 --virtual-time-budget=12000
  --screenshot=<out.png> 'file:///.../deck_single.html#/<n>'
  (snap chromium writes only under $HOME; fragments need a test copy with
  ' fragment fade-up' classes stripped)
- Figures: figuras/sim/*.pdf etc.; raster: pdftoppm -png -r 130
- Thesis PDF: tex/tese.pdf (build: cd tex && latexmk -pdf tese.tex)
- QA PDF: defense/defense-qa.pdf
- Design system: deck CSS in reveal/index.html <style>; thesis figure idiom
  in simulation/results/comparator_frontier/make_metric_stack_figure.py

House rules the deck already satisfies (do not re-litigate): title-slide
emblems are intentional (Holy See + USP/IME official brands); the race/week
animations (a2/a6/a11) are approved and must never be modified; gate-bound
tile texts (682/808/907 margins tile, post-hoc disclosures, span-row labels)
may be flagged but changes route through the bridge.
