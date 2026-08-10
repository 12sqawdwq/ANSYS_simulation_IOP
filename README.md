# Transpalpebral Tonometry: FEM Experiments and Reproducibility Notes

**A reproducible finite-element modeling and validation repository for transpalpebral intraocular-pressure measurement.**

This is a working research repository, not a production calibration package. It contains parameterized ANSYS/APDL models, controlled sweeps, solver-state extraction, data provenance, lightweight results, and analysis code for studying how eyelid mechanics and measurement geometry affect probe response.

Both useful results and results that did not survive later checks are kept visible. In particular, the current model is not mesh independent, several parameters are not identifiable from the available sweeps, and a frozen high-pressure fit did not extrapolate adequately.

![Central-section stress contours from the finite-element workflow](paper/figures/central_section_stress_contours.png)

## Research question

A transpalpebral tonometer measures through the eyelid rather than contacting the cornea directly. The observed probe response can therefore depend on intraocular pressure (IOP), eyelid thickness and stiffness, corneal/scleral response, probe offset, contact evolution, indentation depth, and mesh resolution.

The repository asks:

1. Which simulated observables remain sensitive to IOP under these coupled effects?
2. Can geometric area terms and mechanical load transfer be separated into a defensible correction model?
3. Which parameters are identifiable from the current sweep design?
4. Which conclusions survive mesh and extrapolation checks?

## Model and workflow

```text
parameterized APDL model
        │
        ├── baseline and eccentric probe cases
        ├── eyelid-thickness sweeps
        ├── high-IOP mechanical-transfer sweep
        └── targeted mesh-sensitivity study
        │
        ▼
solver artifacts + run_manifest.csv
        │
        ▼
state extraction and quality checks
        │
        ▼
machine-readable summaries + figures
        │
        ▼
identifiability, sensitivity, and model-limit analysis
```

Formal runs record the Git revision and working-tree state in a manifest. Large native ANSYS solver files remain in external storage; the Git repository keeps models, launchers, lightweight summaries, figures, provenance records, and checks needed to review the analysis.

## Current findings

These findings describe the present model and discretization. They are not clinical performance claims.

### Eyelid-thickness response

- A seven-point 3D thickness sweep is complete.
- With fixed 0.80 mm probe advancement, simulated reaction force rises from **0.6127 N at 0.80 mm eyelid thickness** to **1.4253 N at 2.00 mm**.
- Outer contact area changes little over that sweep.
- The strict geometric ratio `Ae/Ac` is sensitive to angle definition and coarse discretization; it does not reproduce the monotonic trend assumed in earlier placeholder material.

### Probe eccentricity

- The semi-empirical area ratio changes only slightly from 0 to 1 mm offset in the current model.
- At 2 mm offset, internal effective area and the 3D contact extent decrease materially.
- The contact-element proxy falls from 351 to 180 while peak eyelid stress rises from 27.15 kPa to 37.83 kPa.

### Calibration and extrapolation

Three algorithm families are kept separate:

1. **Area conversion:** `PIOP = (Ap/Ac) · Pprobe`.
2. **Empirical rational fit:** `PIOP = a · Pprobe / (1 - b · Pprobe)`.
3. **Mechanical-transfer model:** `PIOP = ηeff · KA · Pprobe = KA · Pprobe / Tmech`.

The first family is no longer treated as a complete algorithm because it systematically underestimates high pressure. The second achieves an in-sample RMSE of approximately **0.954 mmHg** over the frozen 0–50 mmHg configuration, but independent frozen-parameter extrapolation to 52.5–60 mmHg reaches approximately **4.782 mmHg RMSE** and overestimates 60 mmHg by approximately **6.964 mmHg**. This failed calibration test is retained rather than tuned away.

The third family is the current hypothesis being explored. It keeps the geometric area term `KA = Ap/Ac` distinct from the mechanical transmission term. An area ratio, direct interface-force ratio, or algebraic reparameterization is not presented as a validated standalone calibration.

## Limitations and negative results

These limitations are part of the research record:

- **Mesh independence has not been demonstrated.** The 0.30/0.24/0.20 mm audit preserves the direction of the 1.60→2.00 mm response change, but absolute outputs at the two finest levels still differ by as much as **12.31%**.
- **The 1.60 mm feature is not a validated physical threshold.** Its direction is stable in the audited cases; its magnitude remains discretization-dependent.
- **Thickness-specific rational parameters are not identifiable.** Only the 1.25 mm eyelid has a full multi-IOP curve; other thicknesses currently have independent 0 and 20 mmHg endpoints.
- **The high-pressure rational model does not extrapolate adequately.** Frozen-parameter failure is documented rather than tuned away.
- **No algorithm in this repository is a production hardware calibration.** Controlled phantom and hardware measurements are still required.
- **Simulation credibility is bounded by the current geometry, constitutive assumptions, contact formulation, loading path, and available validation data.**

## Reproducibility

The read-only thickness-sensitivity analysis is configured in [`analysis/config.yaml`](analysis/config.yaml). From the repository root:

```powershell
python analysis\run_all.py
```

It writes only below `analysis/outputs/` and writes `output_manifest.csv` last. The manifest records output sizes and SHA-256 hashes. Local ignored solver runs cannot silently enter the formal input inventory.

Run repository tests with:

```bash
python -m pytest -q
```

ANSYS solves are intentionally staged. Smoke cases must pass quality review before coarse or full sweeps are launched; scripts do not advance automatically between stages.

Key reproducibility records:

- [`docs/DATA_PROVENANCE.md`](docs/DATA_PROVENANCE.md) — model levels, parameter differences, and evidence scope.
- [`docs/INDENTATION_SWEEP.md`](docs/INDENTATION_SWEEP.md) — load steps, state decisions, QC, and staged execution.
- [`docs/SCRIPT_INDEX.md`](docs/SCRIPT_INDEX.md) — script responsibilities across the repository.
- [`docs/DOCUMENTATION_POLICY.md`](docs/DOCUMENTATION_POLICY.md) — governance for conclusions, configuration, indexes, logs, and intermediate findings.
- [`thickness_mesh_independence/DETAILED_REPORT.md`](thickness_mesh_independence/DETAILED_REPORT.md) — three mesh levels, fixed-scale contour evidence, and audited solver timing.

## Repository map

| Path | Purpose |
| --- | --- |
| `models/apdl/` | Parameterized APDL models, post-processing macros, and test inputs |
| `src/runners/` | Batch-run entry points and staged sweep orchestration |
| `src/postprocess/` | State extraction, summaries, force/area analysis, and plotting |
| `baseline/` | Centered baseline results and Workbench entry points |
| `offset/` | Eccentricity studies, figures, and reports |
| `thick/` | Eyelid-thickness protocol, data contracts, scripts, and reports |
| `high_iop_mechanical_transfer_t1p25_c0p60/` | Frozen high-IOP configuration, scripts, records, and conclusions |
| `thickness_mesh_independence/` | Targeted mesh-sensitivity design, evidence, and conclusions |
| `analysis/` | Identifiability and thickness-sensitivity analysis pipeline |
| `algorithms/` | Versioned algorithm taxonomy and machine-readable registry |
| `results/summary/` | Lightweight formal summaries and external-result checks |
| `paper/` | Manuscript draft, figures, claim review, and provenance links |
| `tests/` | Regression and pipeline-integrity tests |
| `ops/` | Local/solver-host/partial-clone synchronization tooling |

## Data and storage policy

- Raw ANSYS solver projects and large intermediate fields remain outside Git history.
- Public Git content should contain only data that can be redistributed and reviewed safely.
- Do not add patient-identifiable, private clinical, credential, or device-secret material.
- Historical implementations belong in Git commits, branches, or tags—not duplicate `old`, `final`, or backup directories in the working tree.
- Formal result names stay stable; historical revisions are recovered from Git.

## Status

The repository currently supports reproducible model development, sweep review, and evidence-bounded algorithm research. It does **not** support clinical diagnosis, production calibration, or claims of mesh-converged predictive accuracy.
