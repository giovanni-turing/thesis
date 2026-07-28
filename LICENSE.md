# License

This repository contains three classes of material, licensed as follows.

## Code — MIT

All source code (including `simulation/`, `verification/`, `provenance/`,
`workload/`, `figuras_new/`, `analysis/`, `defense/` build scripts, and
`eda/` tooling) is licensed under the MIT License:

> Copyright (c) 2026 Giovanni Oliveira
>
> Permission is hereby granted, free of charge, to any person obtaining a
> copy of this software and associated documentation files (the
> "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish,
> distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to
> the following conditions:
>
> The above copyright notice and this permission notice shall be included
> in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
> OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
> MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
> IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
> CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
> TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
> SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Dissertation text and produced data — CC-BY 4.0

The dissertation text (`tex/`), defense materials (`defense/` content),
documentation, and all measurement/simulation data produced by this work
(`simulation/results/`, `collector_artifacts/`, `predictors/results/`,
the provenance database dump in the archived record) are licensed under
the Creative Commons Attribution 4.0 International License (CC-BY 4.0):
https://creativecommons.org/licenses/by/4.0/. Attribution: Giovanni
Oliveira, "Forecast-informed vision-pool provisioning for
modality-disaggregated model serving", IME-USP, 2026 — DOI
10.5281/zenodo.21654632.

## Third-party material (respective upstream licenses)

- `template/modelo-latex/` and the vendored `tex/*.sty` files: the
  IME-USP LaTeX model, MIT License (upstream:
  https://github.com/ccsl-usp/modelo-latex; see its LICENSE).
- The Azure multimodal inference trace is NOT redistributed here; obtain
  it from its upstream under its own terms.
- Model weights (`Qwen/Qwen3-VL-8B-Instruct`) are NOT redistributed;
  only content hashes are recorded.
- Vendored skill/data snapshots from `ai-dynamo/*` and `rapidsai/*`
  projects retain their upstream licenses (Apache-2.0 unless noted).
