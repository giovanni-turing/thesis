---
from: claude
ts: 2026-07-28T07:55:00-03:00
re: new
type: question
---

# V04 second pass complete — 19 remaining overfulls reduced to 2, both sub-1pt

Status note (unthreaded; V04's thread awaits your round-2 reply). The offered
second pass over the residual overfull inventory is done: the section-6.7
running-head collision (3 pages), the seven remaining appendix \texttt
paths, the kernel_source line, the TSFM-list paragraph, both related.tex
prose paragraphs, the trace-eda arrival paragraph, and the sim-knees tabular
are all clear. Remaining: 0.99pt on a section heading and 0.13pt on a
description item --- both below visual threshold.

Method constraints held: spacing/breaking-only diff (allowbreak, one
discretionary hyphen, paragraph-local emergencystretch, one sectionmark, one
tabcolsep), zero prose changes, no bound phrase touched. Verification:
build 0 errors / 129 pages, metric-stack gate OK, and pagination proven
byte-identical against the pre-change baseline (toc/lof/lot and every
newlabel anchor) --- nothing moved across any page break. Committing now;
fold the re-check into your next tex sweep at your convenience.
