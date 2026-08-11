# L010 P1 resource-guard abort

## Classification

`resource_guard_abort_with_orphan_process_cleanup`

This directory preserves only lightweight audit evidence from the rejected campaign:

`/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260811T022100Z_d334fd1_L010_t2p00_iop0_20_anchor_serial_np4`

The source was clean commit `d334fd124b768cbb53365fb19f383fa34ec9dbf7`, ANSYS 2025 R2, L010, 2.00 mm, 0 mmHg, 0.28 mm indentation, four MPI ranks and one worker. The planned 20 mmHg state never started.

## What happened

- MAPDL formed a 3,370,950-equation model and selected the distributed sparse out-of-core mode.
- Across four ranks, MAPDL reported 73.775 GB in-core demand, 14.499 GB out-of-core demand and 26.041 GB total solver/non-solver allocation.
- `MemAvailable` fell from 77,680,088 KiB to 12,058,648 KiB (11.50 GiB). The old 15 GiB guard fired at `2026-08-11T02:26:03Z`.
- The old launcher returned 143 after terminating its runner process group, but MAPDL/MPI had created a separate session (`SID=439551`) and continued running.
- The orphan solver was stopped as a complete session at `2026-08-11T04:24:15Z`.
- Load step 1 completed all eight substeps; load step 2 started. Load step 3 and `RUN COMPLETED` were absent. No MAPDL error had appeared before termination, so this is a resource/containment failure, not a demonstrated numerical failure.
- Forty-seven rejected DB/RST/scratch files were removed after inventory and hashing: 90,442,977,929 apparent bytes and 83,147,467,776 allocated bytes. APDL, logs, manifests, hashes and provenance remain externally.

No endpoint from this attempt is accepted; no value of \(q\) can be calculated. `iop0/run_manifest.csv` intentionally has a header but no result row.

## Resource envelope learned from the failed attempt

The new launcher uses:

- one pressure per campaign; 0 mmHg must complete and pass manual QC before a separately authorized 20 mmHg campaign;
- four ranks maximum, one worker and zero retries;
- `MemAvailable >= 90 GiB` and free disk `>=150 GiB` before launch;
- abort floors of 30 GiB available memory and 100 GiB free disk;
- a 10 s monitor interval and 24 h per-case timeout;
- a user-systemd service/cgroup plus random environment token;
- TERM to the complete cgroup/token process set, then KILL after the grace interval;
- residual process snapshots and a hard failure if any process remains.

The ZFS ARC cap is a runtime administrator control and is not persisted by this repository. It must be verified separately before each restart and restored after solving.

## Evidence boundary

`solver_resource_extract.txt` is a small transcription from the retained external `solve.out`; it records that file's SHA-256. The full solver log, APDL files and all accepted large binary evidence remain on 5090d. The deleted DB/RST/scratch belonged only to this incomplete attempt.
