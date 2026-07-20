#!/usr/bin/env python3
"""Run 4 eccentric 3D tonometer cases in parallel: X = 0, 0.5, 1.0, 2.0 mm"""
import os, subprocess, re

PROJECT = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT)

OFFSETS = [0.0, 0.5, 1.0, 2.0]

jobs = []
for off in OFFSETS:
    name = f'e3d_x{off:.1f}'.replace('.', 'p')
    sdir = f'scratch_{name}'
    os.makedirs(sdir, exist_ok=True)
    # copy macro into scratch dir
    subprocess.run(f'cp param_eye_3d.mac {sdir}/', shell=True)
    # driver
    drv = f'{sdir}/drv.dat'
    with open(drv, 'w') as f:
        f.write(f'xoff_val = {off/1000.0}\n*use,param_eye_3d.mac,xoff_val\n')
    cmd = (
        f'ANSYSLMD_LICENSE_FILE=1055@localhost ANSYS_LOCK=OFF '
        f'/ansys_inc/v252/ansys/bin/ansys252 -b -np 4 '
        f'-dir {os.path.abspath(sdir)} '
        f'-i {os.path.abspath(drv)} '
        f'-o {os.path.abspath(sdir)}/out.txt -j {name}'
    )
    jobs.append((name, cmd, sdir))

print(f"Launching {len(jobs)} parallel 3D eccentric cases...")
procs = []
for name, cmd, sdir in jobs:
    p = subprocess.Popen(f'{cmd} > /tmp/e3d_{name}.log 2>&1', shell=True, executable='/bin/bash')
    procs.append((name, p, sdir))

print("\n=== RESULTS ===")
for name, p, sdir in procs:
    p.wait()
    try:
        with open(f'{sdir}/out.txt') as f:
            c = f.read()
        ok = 'RUN COMPLETED' in c
        errs = c.count('*** ERROR ***')
        def grab(pat):
            m = re.search(pat + r'\s*=\s*([\-\d.E+]+)', c)
            return m.group(1) if m else 'N/A'
        sc = grab('CORNEA max SEQV')
        se = grab('EYELID max SEQV')
        cs = grab(r'Contact status sum \(probe-eyelid\)')
        ca = grab('Total contact element area')
        fr = grab('Reaction FY at limbus')
        print(f"  {name}: {'OK' if ok else 'FAIL'} {errs}err | cornea={sc}Pa eyelid={se}Pa "
              f"cstat={cs} carea={ca}m2 FY={fr}N")
    except Exception as e:
        print(f"  {name}: {e}")

print("\nDone!")
