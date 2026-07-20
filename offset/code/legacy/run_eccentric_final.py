#!/usr/bin/env python3
"""
FINAL APPROACH:
1. CR3 (probe-eyelid): KEEP BONDED (only way force transmits with this geometry)
2. CR2 (eyelid-cornea): frictionless (allows differential sliding at different offsets)
3. X-axis offsets simulate eccentric probe placement
4. With bonded CR3, different X offsets produce different eyelid-cornea contact geometries
   because the eyelid wraps differently around the cornea at each position.
5. Displacement = 0.3mm, 4 parallel cases, diagnostic output per case.
"""

import os, sys, shutil, subprocess, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

OFFSETS_X_MM = [0.0, 0.5, 1.0, 2.0]
DISPLACEMENT_MM = 0.3

# Fix CR2 (eyelid-cornea): bonded -> frictionless
cr2 = None
for i, L in enumerate(lines):
    if 'Contact Region 2' in L:
        cr2 = i; break

for i in range(cr2, min(cr2 + 200, len(lines))):
    L = lines[i]
    if 'keyo,cid,12,5' in L:
        lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0')
        print(f"CR2: bonded->frictionless at line {i+1}")
        break

# Disable DMP split
for i, L in enumerate(lines):
    if 'cncheck,dmp' in L:
        lines[i] = L.replace('cncheck,dmp', 'cncheck')
        break

jobs = []
for offset_x in OFFSETS_X_MM:
    case_name = f'case_x{offset_x:.1f}'.replace('.', 'p')
    case_dir = f'{case_name}'
    if os.path.exists(case_dir):
        shutil.rmtree(case_dir)

    shutil.copytree('yeyeye_files', case_dir)
    os.makedirs(f'{case_dir}/dp0/SYS/MECH', exist_ok=True)

    modified = list(lines)
    solu_idx = None
    for i, L in enumerate(modified):
        if L.strip() == '/solu':
            solu_idx = i; break

    offset_m = offset_x / 1000.0
    disp_m = DISPLACEMENT_MM / 1000.0

    # X-offset patch
    patch = f"""
/com,==== ECCENTRIC X={offset_x:.1f}mm DISP={DISPLACEMENT_MM}mm CR2=fricless CR3=bonded ====
/prep7
esel,s,type,,4
nsle,s
*get,nn,node,0,count
*get,nmin,node,0,num,min
*do,i,1,nn
  nmodif,nmin,NX(nmin)+{offset_m}
  *get,nmin,node,nmin,nxth
*enddo
/com,--- X+{offset_x:.1f}mm (%nn% nodes) ---
nsel,all
esel,all
fini
"""
    for j, bl in enumerate(patch.rstrip('\n').split('\n')):
        modified.insert(solu_idx + j, bl + '\n')

    # Modify displacement
    for i, L in enumerate(modified):
        if '_loadvari59yp(3,1,1) = 2.e-003' in L:
            modified[i] = L.replace('2.e-003', f'{disp_m:.6e}'.replace('e-0', 'e-'))
            break

    # Append diagnostic
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
*get,s3max,sort,0,max
/com,=== YANPI MAX SEQV = %s3max% Pa ===
allsel
esel,s,mat,,2
nsle,s
nsort,s,eqv
*get,s2max,sort,0,max
/com,=== CONEAR MAX SEQV = %s2max% Pa ===
allsel
fini
"""
    with open(ds_path := f'{case_dir}/dp0/SYS/MECH/ds.dat', 'a') as f:
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

print(f"Launching {len(jobs)} parallel solves with bonded CR3 + frictionless CR2...")
procs = []
for name, cmd in jobs:
    p = subprocess.Popen(f'{cmd} > /tmp/ansys_final_{name}.log 2>&1', shell=True, executable='/bin/bash')
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
        # Extract diagnostics
        fy_line = re.search(r'=== FY_REACTION = ([\d.E+\-]+)', c)
        s3_line = re.search(r'=== YANPI MAX SEQV = ([\d.E+\-]+)', c)
        s2_line = re.search(r'=== CONEAR MAX SEQV = ([\d.E+\-]+)', c)
        fy = fy_line.group(1) if fy_line else 'N/A'
        s3 = s3_line.group(1) if s3_line else 'N/A'
        s2 = s2_line.group(1) if s2_line else 'N/A'
        print(f"  {name}: {'OK' if ok else 'FAIL'} {errs}err {elapsed}s FY={fy}N yanpi={s3}Pa conear={s2}Pa")
    except Exception as e:
        print(f"  {name}: error - {e}")

print("\nDone!")
