# Dataset provenance

`../AzureLMMInferenceTrace_multimodal.csv.gz` = **AzureLMMInferenceDataset2025**
(Microsoft Azure Public Dataset), traces of a production multimodal-model
inference cluster, 2024-10-15 → 2024-10-22.

- Dataset doc: `AzureLMMInferenceDataset2025.md` (mirrored here; upstream:
  github.com/Azure/AzurePublicDataset). License: CC-BY.
- Official schema note: **ContextTokens includes text AND image tokens** —
  confirms EDA §A's empirical finding.
- Companion paper: *ModServe: Modality- and Stage-Aware Resource
  Disaggregation for Scalable Multimodal Model Serving*, Qiu et al.,
  SoCC 2025 — `ModServe_arXiv2502.00937.pdf` (arXiv:2502.00937,
  DOI 10.1145/3772052.3772254).
- Official example notebook: `AzureLMMInferenceDataset2025.ipynb`
  (mirrored from upstream `analysis/`).
