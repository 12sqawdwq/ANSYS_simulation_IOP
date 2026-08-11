# Formal session-guard validation

- Status: `formal_clean_commit_session_guard_validation_complete`
- Source commit: `c62987d795711052170f3538517e38fff5c0aa18`
- External root: `/home/xuanyu/PROJECT/ziyu/blueknow-data/thickness_mesh_independence/20260811T063315Z_c62987d7_session_guard_validation`
- ANSYS started: no
- Numerical endpoint created: no

Two tests ran from a clean 5090d worktree:

1. `test_session_guard_5090d.sh` created a parent and two nested `setsid` children in different SID/PGID values. The MAPDL/Hydra-named children ignored TERM. The guard escalated to KILL and reported no cgroup/token residual.
2. `test_anchor_launcher_signal_5090d.sh` drove the complete anchor launcher with a fake solver. It passed the commit and resource gates, created the user-systemd unit, entered monitoring, then received TERM. The launcher returned the expected 143, wrote `CAMPAIGN_INCOMPLETE`, escalated TERM to KILL, and left no fixture process or active `blueknow-*` unit.

The helper contained three processes before termination. Both tests preserve PID, PPID, SID, PGID, user, command name and argv snapshots. `final_residual_check.txt` records zero fixture processes and zero active test units after both tests.

This validates process containment and launcher signal cleanup, not MAPDL convergence or resource sufficiency. It authorizes only a separately reviewed restart of L010, 2.00 mm, 0 mmHg in a new campaign root. It does not authorize 20 mmHg, L005, global 0.10 mm, or any numerical claim.
