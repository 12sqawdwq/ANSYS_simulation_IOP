#!/usr/bin/env python3
"""Extract Y-extent of each body from ds.dat to diagnose probe-eyelid overlap."""
import os
os.chdir('/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim')

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# Parse NBLOCK node coords
node_y = {}
for i, line in enumerate(lines):
    if line.startswith('nblock,'):
        for j in range(i+2, len(lines)):
            L = lines[j].rstrip()
            if L.startswith('/') or L.startswith('*') or L.startswith('et,') or L.startswith('eblock'):
                break
            f_ = L.split()
            if len(f_) >= 4:
                try:
                    node_y[f_[0]] = float(f_[2])  # Y coordinate
                except ValueError:
                    pass
        break

print(f"Parsed {len(node_y)} nodes")

# Find each body's element block and collect its nodes
bodies = {1: 'jiamo(cornea outer)', 2: 'conear', 3: 'yanpi(eyelid)', 4: 'PLA(probe)'}
body_markers = {
    1: "Elements for Body 1",
    2: "Elements for Body 2",
    3: "Elements for Body 3",
    4: "Elements for Body 4",
}

for bid, marker in body_markers.items():
    # find marker
    start = None
    for i, line in enumerate(lines):
        if marker in line:
            for j in range(i+1, i+12):
                if lines[j].startswith('eblock,'):
                    start = j
                    nel = int(lines[j].strip().split(',')[4])
                    break
            break
    if start is None:
        print(f"Body {bid}: eblock not found")
        continue
    # collect all integers that are node IDs
    ys = []
    seen = set()
    for j in range(start+2, len(lines)):
        L = lines[j].rstrip()
        if L.startswith('/com,***') or L.startswith('eblock') or (L.startswith('-1') and len(L.strip())<4):
            # heuristic stop: next section
            if '/com,***' in L and 'Elements for Body' not in L:
                break
        if L.startswith('/') or L.startswith('keyo') or L.startswith('*') or L.startswith('et,'):
            break
        for tok in L.split():
            if tok in node_y and tok not in seen:
                seen.add(tok)
                ys.append(node_y[tok])
    if ys:
        print(f"Body {bid} {bodies[bid]:22s}: Y = [{min(ys)*1000:+8.3f}, {max(ys)*1000:+8.3f}] mm  ({len(ys)} nodes)")
    else:
        print(f"Body {bid}: no nodes collected")
