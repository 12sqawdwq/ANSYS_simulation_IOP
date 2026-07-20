#!/usr/bin/env python3
"""
CRITICAL FIX: Contact Region 2 (eyelid-cornea) must be NON-bonded
to produce differential internal contact area at different X offsets.

Physics: Probe glued to eyelid (region 3 bonded).
Eyelid slides over cornea (region 2 frictionless).
At different X offsets, eyelid wraps around cornea differently → distinct Ac.

4 cases: X = 0.0, 0.5, 1.0, 2.0 mm, disp = 0.3 mm, parallel.
"""

import os, sys, shutil, subprocess, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

OFFSETS_X_MM = [0.0, 0.5, 1.0, 2.0]
DISPLACEMENT_MM = 0.3

print(f"Fixing Contact Region 2 (eyelid-cornea): bonded -> frictionless")
print(f"Generating {len(OFFSETS_X_MM)} cases: X={OFFSETS_X_MM}mm, disp={DISPLACEMENT_MM}mm")

# ============================================================
# First, fix Contact Region 2 (eyelid-cornea) in the base lines
# Find "Contact Region 2" marker and fix keyo,cid,12,5 -> keyo,cid,12,0
# ============================================================
cr2 = None
for i, L in enumerate(lines):
    if 'Contact Region 2' in L:
        cr2 = i; break

if cr2 is None:
    print("FATAL: Contact Region 2 not found"); sys.exit(1)

for i in range(cr2, min(cr2 + 200, len(lines))):
    L = lines[i]
    if 'keyo,cid,12,5' in L and 'bonded always' in L:
        lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0').replace('bonded always', 'frictionless (was bonded)')
        print(f"  CR2 KEYOPT(12) bonded->frictionless at line {i+1}")
        break
    elif 'keyo,cid,9,1' in L and 'ignore initial gaps' in L:
        lines[i] = L.replace('keyo,cid,9,1', 'keyo,cid,9,0').replace('ignore initial gaps/penetration', 'include gaps')
        print(f"  CR2 KEYOPT(9) ignore->include gaps at line {i+1}")

# ============================================================
# Also fix CNCHECK in base lines (once, before cases)
# ============================================================
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
/com,****************************************************
/com,*** ECCENTRIC CASE: X={offset_x:.1f}mm, DISP={DISPLACEMENT_MM}mm
/com,*** CR2=frictionless (eyelid slides on cornea)
/com,*** CR3=bonded (probe glued to eyelid)
/com,****************************************************
/prep7
esel,s,type,,4
nsle,s
*get,nn,node,0,count
*get,nmin,node,0,num,min
*do,i,1,nn
  nmodif,nmin,NX(nmin)+{offset_m}
  *get,nmin,node,nmin,nxth
*enddo
nsel,all
esel,all
/com,--- X offset {offset_x:.1f}mm (%nn% nodes) ---
fini
"""
    for j, bl in enumerate(patch.rstrip('\n').split('\n')):
        modified.insert(solu_idx + j, bl + '\n')

    # Smaller displacement
    for i, L in enumerate(modified):
        if '_loadvari59yp(3,1,1) = 2.e-003' in L:
            val_str = f'{disp_m:.6e}'.replace('e-0', 'e-')
            modified[i] = L.replace('2.e-003', val_str)
            break

    ds_path = f'{case_dir}/dp0/SYS/MECH/ds.dat'
    with open(ds_path, 'w', encoding='utf-8') as f:
        f.writelines(modified)

    with open('yeyeye.wbpj', 'r', encoding='utf-8', errors='replace') as f:
        wbpj = f.read()
    now = datetime.now(timezone.utc)
    wbpj = re.sub(r'<timestamp-max valType="Int64">\d+</timestamp-max>',
                  f'<timestamp-max valType="Int64">{int(now.timestamp())}</timestamp-max>', wbpj)
    wbpj = re.sub(r'<last-saved-utc valType="String">[^<]+</last-saved-utc>',
                  f'<last-saved-utc valType="String">{now.strftime("%m/%d/%Y %H:%M:%S")}</last-saved-utc>', wbpj)
    with open(f'{case_dir}/yeyeye.wbpj', 'w', encoding='utf-8') as f:
        f.write(wbpj)

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
    logfile = f'/tmp/ansys_v2_{name}.log'
    p = subprocess.Popen(f'{cmd} > {logfile} 2>&1', shell=True, executable='/bin/bash')
    procs.append((name, p, logfile))

for name, p, logfile in procs:
    p.wait()
    try:
        with open(f'scratch_{name}/solve.out', 'r') as f2:
            content = f2.read()
        completed = 'RUN COMPLETED' in content
        errors = content.count('*** ERROR ***')
        m = re.search(r'Elapsed Time \(sec\)\s*=\s*([\d.]+)', content)
        elapsed = m.group(1) if m else '?'
        print(f"  {name}: {'OK' if completed else 'FAIL'}, {errors} errors, {elapsed}s")
    except:
        print(f"  {name}: output error")

print("\nDone!")
