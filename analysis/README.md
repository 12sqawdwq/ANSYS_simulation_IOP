# Eyelid-thickness sensitivity analysis

Run from the repository root:

```powershell
E:\SOFTWARE\annaconda\annaconda_evn\python.exe analysis\run_all.py
```

The pipeline is read-only with respect to source data. It writes only below
`analysis/outputs/`. Configuration, mappings, units, thresholds, bootstrap
count, and the stiffness window are in `config.yaml`. Data inventory is limited
to tracked files plus non-ignored untracked files, so local solver runs excluded
by `.gitignore` cannot silently change the formal inventory. `run_all.py` writes
`output_manifest.csv` last; every listed size and SHA-256 must verify after a
successful run.

Important design limitation: only the 1.25 mm eyelid has a full multi-IOP
curve. Other thicknesses have independent 0 and 20 mmHg endpoints. The code
therefore records their rational-model parameters as non-identifiable; it does
not fill them using shared parameters or interpolation.
