# Eyelid-thickness sensitivity analysis

Run from the repository root:

```powershell
E:\SOFTWARE\annaconda\annaconda_evn\python.exe analysis\run_all.py
```

The pipeline is read-only with respect to source data. It writes only below
`analysis/outputs/`. Configuration, mappings, units, thresholds, bootstrap
count, and the stiffness window are in `config.yaml`.

Important design limitation: only the 1.25 mm eyelid has a full multi-IOP
curve. Other thicknesses have independent 0 and 20 mmHg endpoints. The code
therefore records their rational-model parameters as non-identifiable; it does
not fill them using shared parameters or interpolation.
