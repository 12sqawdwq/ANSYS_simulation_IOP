#!/usr/bin/env python3
"""
Radical fix: ALL contacts frictional (mu=0.3 probe-eyelid, mu=0.1 eyelid-cornea).
CR1 (cornea layers): keep bonded (biological attachment is reasonable)
CR2 (eyelid-cornea): frictionless with KEYOPT(12)=0, KEYOPT(9)=0
CR3 (probe-eyelid): frictional mu=0.3, KEYOPT(12)=0, KEYOPT(9)=0
No DMP split (cncheck only).
Add FKN=50 for stiff contact to ensure load transfer.
X offsets: 0, 0.5, 1.0, 2.0mm, disp=0.3mm. Parallel 4 cases.
"""

import os, sys, shutil, subprocess, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

OFFSETS_X_MM = [0.0, 0.5, 1.0, 2.0]
DISPLACEMENT_MM = 0.3

# ============================================================
# Fix contacts in base lines
# ============================================================
# CR2 markers
cr2 = None
for i, L in enumerate(lines):
    if 'Contact Region 2' in L:
        cr2 = i; break

# CR3 markers
cr3 = None
for i, L in enumerate(lines):
    if 'Contact Region 3' in L:
        cr3 = i; break

print(f"CR2 at line {cr2+1}, CR3 at line {cr3+1}")

# Fix CR2: frictionless (allow eyelid sliding over cornea)
for i in range(cr2, min(cr2 + 200, len(lines))):
    L = lines[i]
    if 'keyo,cid,12,5' in L:
        lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0').replace('bonded always', 'frictionless')
        print(f"  CR2: bonded->frictionless")
        break

# Fix CR3: frictional MU=0.3 (probe grips eyelid surface)
for i in range(cr3, min(cr3 + 200, len(lines))):
    L = lines[i]
    if 'keyo,cid,12,5' in L:
        lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0').replace('bonded always', 'frictional mu=0.3')
        print(f"  CR3: bonded->frictional mu=0.3")
        break

# Add friction coeff to CR3: modify rmore for real 9 (contact) to set MU=0.3
# Real constant field 16 for CONTA174 = MU (friction coefficient)
for i in range(cr3, min(cr3 + 200, len(lines))):
    L = lines[i]
    # Add MU right after the CNOF line (field 10)
    if 'rmod,cid,12,0.' in L:
        # Insert MU after this line if not present
        insert_pos = i + 1
        mu_line = 'rmod,cid,16,0.3      ! MU = 0.3 friction coefficient\n'
        lines.insert(insert_pos, mu_line)
        print(f"  CR3: added MU=0.3 friction at line {insert_pos+1}")
        break

# Disable DMP contact split
for i, L in enumerate(lines):
    if 'cncheck,dmp' in L:
        lines[i] = L.replace('cncheck,dmp', 'cncheck')
        break

# ============================================================
# Generate cases
# ============================================================
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

    patch = f"""
/com,==== ECCENTRIC CASE X={offset_x:.1f}mm DISP={DISPLACEMENT_MM}mm CR2=fricless CR3=fric0.3 ====
/prep7
esel,s,type,,4
nsle,s
*get,nn,node,0,count
*get,nmin,node,0,num,min
*do,i,1,nn
  nmodif,nmin,NX(nmin)+{offset_m}
  *get,nmin,node,nmin,nxth
*enddo
/com,--- X+{offset_x:.1f}mm (%nn% probe nodes) ---
nsel,all
esel,all
fini
"""
    for j, bl in enumerate(patch.rstrip('\n').split('\n')):
        modified.insert(solu_idx + j, bl + '\n')

    # Smaller displacement
    for i, L in enumerate(modified):
        if '_loadvari59yp(3,1,1) = 2.e-003' in L:
            modified[i] = L.replace('2.e-003', f'{disp_m:.6e}'.replace('e-0', 'e-'))
            break

    ds_path = f'{case_dir}/dp0/SYS/MECH/ds.dat'
    with open(ds_path, 'w', encoding='utf-8') as f:
        f.writelines(modified)

    scratch_dir = f'scratch_{case_name}'
    os.makedirs(scratch_dir, exist_ok=True)

    # Add diagnostic POST1 to each ds.dat
    diag = f"""
/post1
set,last
allsel
fsum
*get,fy,fsum,0,item,fy
*cfopen,{case_name}_diag,txt
*vwrite,'FY_REACTION',fy
(A,1X,E15.6)
*cfclos
fini
"""
    with open(ds_path, 'a') as f:
        f.write(diag)

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
    p = subprocess.Popen(f'{cmd} > /tmp/ansys_v3_{name}.log 2>&1', shell=True, executable='/bin/bash')
    procs.append((name, p))

results = {}
for name, p in procs:
    p.wait()
    diag_file = f'scratch_{name}/{name}_diag.txt'
    try:
        if os.path.exists(diag_file):
            with open(diag_file) as f:
                results[name] = f.read().strip()
        with open(f'scratch_{name}/solve.out') as f:
            c = f.read()
        ok = 'RUN COMPLETED' in c
        errs = c.count('*** ERROR ***')
        m = re.search(r'Elapsed Time \(sec\)\s*=\s*([\d.]+)', c)
        elapsed = m.group(1) if m else '?'
        print(f"  {name}: {'OK' if ok else 'FAIL'}, {errs} err, {elapsed}s, diag={results.get(name, 'no')}")
    except Exception as e:
        print(f"  {name}: error - {e}")

print("\n=== COMPARISON ===")
for name, r in results.items():
    print(f"  {name}: {r}")
