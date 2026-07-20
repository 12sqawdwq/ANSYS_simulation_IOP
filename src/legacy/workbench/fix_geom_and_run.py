#!/usr/bin/env python3
"""
GEOMETRY FIX: Extend probe top surface in +Y by 2mm to ensure overlap with eyelid.
Then apply X offsets for eccentric measurement analysis.
All 3 contact pairs: bonded (force transfer guaranteed after geometry fix).
4 cases parallel: X = 0, 0.5, 1.0, 2.0 mm. Displacement = 0.3 mm.
"""

import os, sys, shutil, subprocess, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

OFFSETS_X_MM = [0.0, 0.5, 1.0, 2.0]
DISPLACEMENT_MM = 0.3
PROBE_EXTEND_MM = 2.0  # Extend probe top by 2mm in +Y

# Disable DMP split
for i, L in enumerate(lines):
    if 'cncheck,dmp' in L:
        lines[i] = L.replace('cncheck,dmp', 'cncheck')
        break

# CR2: change to frictionless to allow eyelid-cornea differential sliding
cr2 = None
for i, L in enumerate(lines):
    if 'Contact Region 2' in L:
        cr2 = i; break
if cr2:
    for i in range(cr2, min(cr2 + 200, len(lines))):
        L = lines[i]
        if 'keyo,cid,12,5' in L:
            lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0')
            print(f"CR2: bonded->frictionless")
            break

print(f"Probe Y-extend: +{PROBE_EXTEND_MM}mm, X-offsets: {OFFSETS_X_MM}, disp: {DISPLACEMENT_MM}mm")

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
    extend_m = PROBE_EXTEND_MM / 1000.0
    disp_m = DISPLACEMENT_MM / 1000.0

    # GEOMETRY MODIFICATION + X-offset patch (simpler: move entire probe)
    patch = f"""
/com,=====================================================
/com,*** GEOMETRY FIX: Move entire probe +{PROBE_EXTEND_MM}mm in Y
/com,*** ECCENTRIC: X offset = {offset_x:.1f}mm
/com,*** DISPLACEMENT = {DISPLACEMENT_MM}mm
/com,*** CR2 = frictionless, CR1/CR3 = bonded
/com,=====================================================
/prep7
esel,s,type,,4              ! Probe elements
nsle,s                      ! Probe nodes
*get,nn,node,0,count
*get,nmin,node,0,num,min
*do,i,1,nn
  nmodif,nmin,NX(nmin)+{offset_m},NY(nmin)+{extend_m}
  *get,nmin,node,nmin,nxth
*enddo
/com,--- Probe: Y+{PROBE_EXTEND_MM}mm, X+{offset_x:.1f}mm (%nn% nodes) ---
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
*get,puy_max,sort,0,max
/com,=== PROBE UY MAX = %puy_max% m ===
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

print(f"\nLaunching {len(jobs)} parallel solves...")
procs = []
for name, cmd in jobs:
    p = subprocess.Popen(f'{cmd} > /tmp/ansys_geo_{name}.log 2>&1', shell=True, executable='/bin/bash')
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
        print(f"  {name}: {'OK' if ok else 'FAIL'} {errs}err {elapsed}s "
              f"FY={fy.group(1) if fy else 'N/A'}N "
              f"yanpi={s3.group(1) if s3 else 'N/A'}Pa "
              f"conear={s2.group(1) if s2 else 'N/A'}Pa "
              f"pUY={puy.group(1) if puy else 'N/A'}m")
    except Exception as e:
        print(f"  {name}: error - {e}")

print("\nDone!")
