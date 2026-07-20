#!/usr/bin/env python3
"""
PLAN B: 1mm offset with WORKING contact detection.

Root-cause fixes vs previous failed attempt:
  1. PINB sign: CONTA174 PINB positive = SCALE factor, negative = ABSOLUTE.
     Previous +0.002 => tiny scaled pinball. Correct = -0.002 (absolute 2mm).
  2. Set PINB directly in the contact REAL-CONSTANT block (before DMP split),
     via rmod,cid,6 and rmod,tid,6 -- so it survives split (no post-hoc rmodif).
  3. Contact Region 3: bonded->standard (KEYOPT12 5->0), include gaps (KEYOPT9 1->0),
     so probe can approach, contact, and separate physically.
  4. Probe offset -1mm via NMODIF (unchanged, direction confirmed -Y).

Direction reminder:
  +Y = contact normal, probe pushes +Y toward eyelid.
  Offset probe -1mm in Y (further from eyelid). Displacement 0->2mm +Y.
  So probe closes 1mm gap then compresses ~1mm.
"""

import os, sys, shutil, re
from datetime import datetime, timezone

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
print(f"Read {len(lines)} lines")

# ============================================================
# 1. NMODIF offset block before /solu
# ============================================================
apdl_offset = """/com,****************************************************
/com,*** OFFSET PROBE 1mm AWAY FROM EYELID (-Y)
/com,****************************************************
/prep7
esel,s,type,,4
nsle,s
*get,n_probe,node,0,count
*get,nmin,node,0,num,min
*do,i,1,n_probe
  nmodif,nmin,,NY(nmin)-0.001
  *get,nmin,node,nmin,nxth
*enddo
/com,--- Probe offset: %n_probe% nodes -1mm in Y ---
nsel,all
esel,all
fini
"""
solu_idx = None
for i, line in enumerate(lines):
    if line.strip() == '/solu':
        solu_idx = i
        break
if solu_idx is None:
    print("FATAL: /solu not found"); sys.exit(1)

for j, bl in enumerate(apdl_offset.rstrip('\n').split('\n')):
    lines.insert(solu_idx + j, bl + '\n')
print(f"1. NMODIF block inserted at line {solu_idx+1}")

# ============================================================
# 2. Fix Contact Region 3: type, gaps, and PINB (absolute 2mm)
# ============================================================
c3 = None
for i, line in enumerate(lines):
    if 'Contact Region 3' in line:
        c3 = i; break
if c3 is None:
    print("FATAL: Contact Region 3 not found"); sys.exit(1)

fixes = {'k12': False, 'k9': False, 'k18': False, 'k10': False, 'pinb_cid': False, 'pinb_tid': False, 'fkn_cid': False, 'fkn_tid': False}
for i in range(c3, min(c3 + 250, len(lines))):
    L = lines[i]
    if 'keyo,cid,12,5' in L and not fixes['k12']:
        lines[i] = L.replace('keyo,cid,12,5', 'keyo,cid,12,0').replace('bonded always', 'standard (was bonded)')
        fixes['k12'] = True
        print(f"2. KEYOPT(12) bonded->standard at line {i+1}")
    elif 'keyo,cid,9,1' in L and not fixes['k9']:
        lines[i] = L.replace('keyo,cid,9,1', 'keyo,cid,9,0').replace('ignore initial gaps/penetration', 'include gaps')
        fixes['k9'] = True
        print(f"3. KEYOPT(9) ignore->include gaps at line {i+1}")
    elif 'keyo,cid,18,1' in L and not fixes['k18']:
        lines[i] = L.replace('keyo,cid,18,1', 'keyo,cid,18,0').replace('small sliding turned on by application', 'FINITE sliding (was small)')
        fixes['k18'] = True
        print(f"3b. KEYOPT(18) small->finite sliding at line {i+1}")
    elif 'keyo,cid,10,0' in L and not fixes['k10']:
        lines[i] = L.replace('keyo,cid,10,0', 'keyo,cid,10,2').replace('adjust contact stiffness each NR iteration (from Program Controlled setting)', 'update stiffness EACH iteration (reduce penetration)')
        fixes['k10'] = True
        print(f"3c. KEYOPT(10) update stiffness each iteration at line {i+1}")
    elif 'rmod,cid,3,10.' in L and not fixes['fkn_cid']:
        lines[i] = L.replace('rmod,cid,3,10.', 'rmod,cid,3,100.').replace('! FKN', '! FKN = 100 (stiff, prevent penetration)')
        fixes['fkn_cid'] = True
        print(f"3d. FKN(cid) 10->100 at line {i+1}")
    elif 'rmod,tid,3,10.' in L and not fixes['fkn_tid']:
        lines[i] = L.replace('rmod,tid,3,10.', 'rmod,tid,3,100.').replace('! FKN', '! FKN = 100')
        fixes['fkn_tid'] = True
        print(f"3e. FKN(tid) 10->100 at line {i+1}")
    elif 'rmod,cid,6,0.' in L and not fixes['pinb_cid']:
        lines[i] = L.replace('rmod,cid,6,0.', 'rmod,cid,6,-0.002').replace('! PINB', '! PINB = -2mm ABSOLUTE (bridge 1mm gap)')
        fixes['pinb_cid'] = True
        print(f"4. PINB(cid) = -0.002 absolute at line {i+1}")
    elif 'rmod,tid,6,0.' in L and not fixes['pinb_tid']:
        lines[i] = L.replace('rmod,tid,6,0.', 'rmod,tid,6,-0.002').replace('! PINB', '! PINB = -2mm ABSOLUTE')
        fixes['pinb_tid'] = True
        print(f"5. PINB(tid) = -0.002 absolute at line {i+1}")

for k, v in fixes.items():
    if not v:
        print(f"   WARNING: fix '{k}' not applied!")

# ============================================================
# 3. Write project + update wbpj
# ============================================================
DST = 'yeyeye_offset_1mm'
if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree('yeyeye_files', DST)
os.makedirs(f'{DST}/dp0/SYS/MECH', exist_ok=True)

# Append diagnostic block (same as baseline) to verify contact + per-body stress
diag = """
/com,#### PLAN B DIAGNOSTIC ####
/post1
set,last
nsort,u,y
*get,uy_max,sort,0,max
*get,uy_min,sort,0,min
/com,=== MAX UY = %uy_max% m , MIN UY = %uy_min% m ===
nsort,s,eqv
*get,seqv_max,sort,0,max
*get,seqv_node,sort,0,imax
/com,=== MAX SEQV = %seqv_max% Pa at node %seqv_node% ===
esel,s,mat,,1 $ nsle,s $ nsort,s,eqv
*get,s1,sort,0,max
/com,=== jiamo(cornea outer) max SEQV = %s1% Pa ===
allsel $ esel,s,mat,,2 $ nsle,s $ nsort,s,eqv
*get,s2,sort,0,max
/com,=== conear(cornea inner) max SEQV = %s2% Pa ===
allsel $ esel,s,mat,,3 $ nsle,s $ nsort,s,eqv
*get,s3,sort,0,max
/com,=== yanpi(eyelid) max SEQV = %s3% Pa ===
allsel $ esel,s,mat,,4 $ nsle,s $ nsort,s,eqv
*get,s4,sort,0,max
/com,=== PLA(probe) max SEQV = %s4% Pa ===
allsel
fini
"""
lines_out = lines + [diag]

with open(f'{DST}/dp0/SYS/MECH/ds.dat', 'w', encoding='utf-8') as f:
    f.writelines(lines_out)

with open('yeyeye.wbpj', 'r', encoding='utf-8', errors='replace') as f:
    wbpj = f.read()
now = datetime.now(timezone.utc)
wbpj = re.sub(r'<timestamp-max valType="Int64">\d+</timestamp-max>',
              f'<timestamp-max valType="Int64">{int(now.timestamp())}</timestamp-max>', wbpj)
wbpj = re.sub(r'<last-saved-utc valType="String">[^<]+</last-saved-utc>',
              f'<last-saved-utc valType="String">{now.strftime("%m/%d/%Y %H:%M:%S")}</last-saved-utc>', wbpj)
with open(f'{DST}/yeyeye.wbpj', 'w', encoding='utf-8') as f:
    f.write(wbpj)

print(f"\nPlan B ready: {DST}/")
print("  Offset -1mm + standard contact + PINB=-2mm absolute")
