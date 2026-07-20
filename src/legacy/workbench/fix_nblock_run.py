#!/usr/bin/env python3
"""
CORRECT APPROACH: Modify probe node coordinates DIRECTLY in NBLOCK section.
Contact is then defined with the modified geometry → works from the start.
No NMODIF. No second /prep7. No contact element staleness.

Probe: extend +2mm in Y (ensure overlap with eyelid)
X offsets: 0, 0.5, 1.0, 2.0 mm (eccentric measurement)
CR2: frictionless (eyelid slides on cornea)
CR1/CR3: bonded (force transfer works)
Displacement: 0.3mm
"""

import os, sys, shutil, subprocess, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

# ============================================================
# Parse NBLOCK: find all probe nodes via element connectivity
# ============================================================
print("Parsing NBLOCK and element connectivity...")

# Parse node coordinates
nblock_start = None
for i, L in enumerate(lines):
    if L.startswith('nblock,'):
        nblock_start = i
        num_nodes = int(L.strip().split(',')[3])
        break

node_coords = {}  # nid_str -> [x, y, z]
node_line_idx = {}  # nid_str -> line_index
data_start = nblock_start + 2
parsed = 0
for j in range(data_start, len(lines)):
    L = lines[j].rstrip()
    if L.startswith('/') or L.startswith('*') or L.startswith('et,') or L.startswith('eblock'):
        if parsed >= num_nodes * 0.9:  # tolerance
            break
    f_ = L.split()
    if len(f_) >= 4:
        try:
            nid = f_[0]; x, y, z = float(f_[1]), float(f_[2]), float(f_[3])
            node_coords[nid] = [x, y, z]; node_line_idx[nid] = j; parsed += 1
        except ValueError: pass

print(f"  Parsed {len(node_coords)} nodes")

# Parse type 4 (probe) element block to find probe node IDs
probe_nodes = set()
probe_eblock = None
for i, L in enumerate(lines):
    if 'Elements for Body 4' in L:
        for j in range(i+1, i+10):
            if lines[j].startswith('eblock,'):
                probe_eblock = j
                nel = int(lines[j].strip().split(',')[4])
                break
        break

if probe_eblock:
    for j in range(probe_eblock + 2, len(lines)):
        L = lines[j].rstrip()
        if L.startswith('/com,***') or L.startswith('/wb,contact'):
            break
        for tok in L.split():
            if tok in node_coords:
                probe_nodes.add(tok)
    print(f"  Found {len(probe_nodes)} candidate nodes from Body 4 eblock")

# CRITICAL: Also parse type 1 (jiamo) and type 2 (conear) eblocks
# to identify cornea nodes — these must NOT be offset
# BUT only read the FIRST eblock after each body marker (solid elements only)
cornea_nodes = set()
for body_label, eblock_marker in [(1, 'Elements for Body 1'), (2, 'Elements for Body 2')]:
    found_eblock = False
    for i, L in enumerate(lines):
        if eblock_marker in L and not found_eblock:
            for j in range(i+1, min(i+15, len(lines))):
                if lines[j].startswith('eblock,'):
                    for k in range(j+2, len(lines)):
                        L2 = lines[k].rstrip()
                        # Stop at NEXT body marker or contact section
                        if 'Elements for Body' in L2 or '/wb,contact' in L2 or L2.startswith('-1') and len(L2.strip())<=3:
                            break
                        if L2.startswith('/com') or L2.startswith('keyo,'):
                            continue
                        for tok in L2.split():
                            if tok in node_coords:
                                cornea_nodes.add(tok)
                    found_eblock = True
                    break
            if found_eblock:
                break

# PROBE-ONLY: nodes in probe_eblock but NOT in cornea_eblocks
probe_only = probe_nodes - cornea_nodes
print(f"  Probe-only nodes (excl. cornea overlap): {len(probe_only)} (removed {len(probe_nodes & cornea_nodes)} shared)")

# ============================================================
# CR2 fix + CNCHECK fix in base lines
# ============================================================
cr2 = None
for i, L in enumerate(lines):
    if 'Contact Region 2' in L:
        cr2 = i; break
if cr2:
    for i in range(cr2, min(cr2 + 200, len(lines))):
        L = lines[i]
        if 'keyo,cid,12,5' in L:
            lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0')
            print("CR2: bonded->frictionless")
            break

for i, L in enumerate(lines):
    if 'cncheck,dmp' in L:
        lines[i] = L.replace('cncheck,dmp', 'cncheck')
        break

# ============================================================
# Generate cases: directly modify NBLOCK Y coords for probe nodes
# ============================================================
OFFSETS_X_MM = [0.0, 0.5, 1.0, 2.0]
DISPLACEMENT_MM = 0.3
PROBE_Y_EXTEND_MM = 2.0

print(f"\nGenerating cases: X={OFFSETS_X_MM}, Yext={PROBE_Y_EXTEND_MM}mm, disp={DISPLACEMENT_MM}mm")

jobs = []
for offset_x in OFFSETS_X_MM:
    case_name = f'case_x{offset_x:.1f}'.replace('.', 'p')
    case_dir = f'{case_name}'
    if os.path.exists(case_dir):
        shutil.rmtree(case_dir)
    shutil.copytree('yeyeye_files', case_dir)
    os.makedirs(f'{case_dir}/dp0/SYS/MECH', exist_ok=True)

    # Copy and modify node coordinates in NBLOCK section
    modified = list(lines)
    offset_m = offset_x / 1000.0
    extend_m = PROBE_Y_EXTEND_MM / 1000.0

    # Modify only probe-only node lines in NBLOCK
    nmod = 0
    for nid in probe_only:
        if nid in node_line_idx:
            idx = node_line_idx[nid]
            x, y, z = node_coords[nid]
            nx, ny = x + offset_m, y + extend_m
            # Rebuild Fortran format line (1i9,3e20.9e3)
            modified[idx] = f"{int(nid):9d}{nx:20.9E}{ny:20.9E}{z:20.9E}\n"
            nmod += 1

    print(f"  {case_name}: {nmod} probe nodes modified (X+{offset_x}mm, Y+{PROBE_Y_EXTEND_MM}mm)")

    # Modify displacement
    disp_m = DISPLACEMENT_MM / 1000.0
    for i, L in enumerate(modified):
        if '_loadvari59yp(3,1,1) = 2.e-003' in L:
            modified[i] = L.replace('2.e-003', f'{disp_m:.6e}'.replace('e-0', 'e-'))
            break

    # Diagnostic block
    diag = f"""
/post1
set,last
allsel
fsum
*get,fy,fsum,0,item,fy
/com,=== FY_REACTION = %fy% ===
esel,s,mat,,3
nsle,s
nsort,s,eqv
*get,s3,sort,0,max
/com,=== YANPI SEQV = %s3% Pa ===
allsel
esel,s,mat,,2
nsle,s
nsort,s,eqv
*get,s2,sort,0,max
/com,=== CONEAR SEQV = %s2% Pa ===
allsel
esel,s,mat,,4
nsle,s
nsort,u,y
*get,puy,sort,0,max
/com,=== PROBE UY MAX = %puy% m ===
allsel
esel,s,mat,,3
nsle,s
nsort,u,y
*get,ey_uy,sort,0,max
/com,=== EYELID UY MAX = %ey_uy% m ===
allsel
fini
"""

    ds_path = f'{case_dir}/dp0/SYS/MECH/ds.dat'
    with open(ds_path, 'w', encoding='utf-8') as f:
        f.writelines(modified)
    with open(ds_path, 'a') as f:
        f.write(diag)

    scratch_dir = f'scratch_{case_name}'
    os.makedirs(scratch_dir, exist_ok=True)

    cmd = (
        f'ANSYSLMD_LICENSE_FILE=1055@localhost ANSYS_LOCK=OFF '
        f'/ansys_inc/v252/ansys/bin/ansys252 -b -np 4 -m 8 '
        f'-dir {os.path.abspath(scratch_dir)} '
        f'-i {os.path.abspath(ds_path)} '
        f'-o {os.path.abspath(scratch_dir)}/solve.out '
        f'-j {case_name}'
    )
    jobs.append((case_name, cmd))

print(f"\nLaunching {len(jobs)} parallel solves (NBLOCK-modified, no NMODIF)...")
procs = []
for name, cmd in jobs:
    p = subprocess.Popen(f'{cmd} > /tmp/ansys_nb_{name}.log 2>&1', shell=True, executable='/bin/bash')
    procs.append((name, p))

for name, p in procs:
    p.wait()
    try:
        with open(f'scratch_{name}/solve.out') as f:
            c = f.read()
        ok = 'RUN COMPLETED' in c
        errs = c.count('*** ERROR ***')
        m = re.search(r'Elapsed Time \(sec\)\s*=\s*([\d.]+)', c)
        elapsed = m.group(1) if m else '?'
        fy = re.search(r'=== FY_REACTION = ([\d.E+\-]+)', c)
        s3 = re.search(r'=== YANPI SEQV = ([\d.E+\-]+)', c)
        s2 = re.search(r'=== CONEAR SEQV = ([\d.E+\-]+)', c)
        puy = re.search(r'=== PROBE UY MAX = ([\d.E+\-]+)', c)
        euy = re.search(r'=== EYELID UY MAX = ([\d.E+\-]+)', c)
        print(f"  {name}: {'OK' if ok else 'FAIL'} {errs}err {elapsed}s "
              f"FY={fy.group(1) if fy else 'N/A'}N "
              f"yanpi={s3.group(1) if s3 else 'N/A'}Pa "
              f"conear={s2.group(1) if s2 else 'N/A'}Pa "
              f"pUY={puy.group(1) if puy else 'N/A'}m "
              f"eUY={euy.group(1) if euy else 'N/A'}m")
    except Exception as e:
        print(f"  {name}: error - {e}")

print("\nDone!")
