#!/usr/bin/env python3
"""
Generate 4 eccentric indentation cases from baseline model.
X-axis lateral offsets: 0.0, 0.5, 1.0, 2.0 mm
Probe displacement: 0.3 mm (per reference document)
Keep bonded contact (working chain: probe→eyelid→cornea)
Run all 4 cases in parallel on server.

Reference: 偏心测量曲线分析.md
"""

import os, sys, shutil, subprocess, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

# Read original ds.dat (baseline, bonded, works)
with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

OFFSETS_X_MM = [0.0, 0.5, 1.0, 2.0]
DISPLACEMENT_MM = 0.3  # per reference document

print(f"Generating {len(OFFSETS_X_MM)} cases: X offsets={OFFSETS_X_MM}mm, displacement={DISPLACEMENT_MM}mm")

jobs = []

for offset_x in OFFSETS_X_MM:
    case_name = f'case_x{offset_x:.1f}'.replace('.', 'p')
    case_dir = f'{case_name}'

    if os.path.exists(case_dir):
        shutil.rmtree(case_dir)

    # Copy base project
    shutil.copytree('yeyeye_files', case_dir)
    os.makedirs(f'{case_dir}/dp0/SYS/MECH', exist_ok=True)

    # Build modified ds.dat
    modified = list(lines)

    # Insert offset + displacement changes before /solu
    solu_idx = None
    for i, L in enumerate(modified):
        if L.strip() == '/solu':
            solu_idx = i
            break

    offset_m = offset_x / 1000.0
    disp_m = DISPLACEMENT_MM / 1000.0

    patch = f"""
/com,****************************************************
/com,*** CASE: X OFFSET = {offset_x:.1f}mm, DISP = {DISPLACEMENT_MM}mm
/com,****************************************************
/prep7
! Apply X offset to probe nodes (lateral eccentricity)
esel,s,type,,4              ! Probe elements
nsle,s
*get,nn,node,0,count
*get,nmin,node,0,num,min
*do,i,1,nn
  nmodif,nmin,NX(nmin)+{offset_m}
  *get,nmin,node,nmin,nxth
*enddo
/com,--- X offset {offset_x:.1f}mm applied to %nn% probe nodes ---
nsel,all
esel,all
fini
"""
    for j, bl in enumerate(patch.rstrip('\n').split('\n')):
        modified.insert(solu_idx + j, bl + '\n')

    # Modify displacement table: use smaller displacement
    for i, L in enumerate(modified):
        if '_loadvari59yp(3,1,1) = 2.e-003' in L:
            val_str = f'{disp_m:.6e}'.replace('e-0', 'e-')
            modified[i] = L.replace('2.e-003', val_str)
            break

    # Also modify CNCHECK to avoid DMP split issues
    for i, L in enumerate(modified):
        if 'cncheck,dmp' in L:
            modified[i] = L.replace('cncheck,dmp', 'cncheck')
            break

    # Write ds.dat
    ds_path = f'{case_dir}/dp0/SYS/MECH/ds.dat'
    with open(ds_path, 'w', encoding='utf-8') as f:
        f.writelines(modified)

    # Copy wbpj
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

    print(f"  {case_name}: X+{offset_x:.1f}mm, disp={DISPLACEMENT_MM}mm, ready")

# ============================================================
# Launch all jobs in parallel
# ============================================================
print(f"\nLaunching {len(jobs)} parallel solves...")

procs = []
for name, cmd in jobs:
    logfile = f'/tmp/ansys_{name}.log'
    p = subprocess.Popen(
        f'{cmd} > {logfile} 2>&1',
        shell=True, executable='/bin/bash'
    )
    procs.append((name, p, logfile))
    print(f"  {name}: PID={p.pid}, log={logfile}")

# Wait for all
print("\nWaiting for all jobs to complete...")
for name, p, logfile in procs:
    p.wait()
    # Check for RUN COMPLETED
    try:
        with open(f'{os.path.abspath("scratch_" + name)}/solve.out', 'r') as f:
            content = f.read()
        completed = 'RUN COMPLETED' in content
        errors = content.count('*** ERROR ***')
        elapsed = 'unknown'
        m = re.search(r'Elapsed Time \(sec\)\s*=\s*([\d.]+)', content)
        if m: elapsed = m.group(1)
        print(f"  {name}: {'OK' if completed else 'FAIL'}, {errors} errors, {elapsed}s")
    except:
        print(f"  {name}: output not found")

print("\nAll jobs complete!")
