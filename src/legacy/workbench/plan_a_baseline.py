#!/usr/bin/env python3
"""
PLAN A: Baseline verification (0 offset, original bonded contact).
Append a POST1 diagnostic block to report:
  - Max UY displacement (does eye deform?)
  - Max von-Mises stress + location (singularity check)
  - Per-body max stress
This confirms the force-transfer chain is healthy before adding offset.
"""

import os, shutil

PROJECT_DIR = '/home/xuanyu/PROJECT/ziyu/ansys_simunation/tonometer_sim'
os.chdir(PROJECT_DIR)

with open('yeyeye_files/dp0/SYS/MECH/ds.dat', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Append diagnostic post-processing at the very end (after existing /post1 fini)
diag_block = """
/com,####################################################
/com,### PLAN A DIAGNOSTIC BLOCK
/com,####################################################
/post1
set,last
! Max UY displacement over whole model
nsort,u,y
*get,uy_max,sort,0,max
*get,uy_min,sort,0,min
/com,=== MAX UY = %uy_max% m , MIN UY = %uy_min% m ===
! Max von-Mises stress and its node
nsort,s,eqv
*get,seqv_max,sort,0,max
*get,seqv_node,sort,0,imax
/com,=== MAX SEQV = %seqv_max% Pa at node %seqv_node% ===
! Per-body max stress: select each material and report
esel,s,mat,,1
nsle,s
nsort,s,eqv
*get,s_jiamo,sort,0,max
/com,=== BODY jiamo(cornea outer) max SEQV = %s_jiamo% Pa ===
allsel
esel,s,mat,,2
nsle,s
nsort,s,eqv
*get,s_conear,sort,0,max
/com,=== BODY conear(cornea inner) max SEQV = %s_conear% Pa ===
allsel
esel,s,mat,,3
nsle,s
nsort,s,eqv
*get,s_yanpi,sort,0,max
/com,=== BODY yanpi(eyelid) max SEQV = %s_yanpi% Pa ===
allsel
esel,s,mat,,4
nsle,s
nsort,s,eqv
*get,s_pla,sort,0,max
/com,=== BODY PLA(probe) max SEQV = %s_pla% Pa ===
allsel
fini
"""

content = content + diag_block

DST = 'yeyeye_baseline'
if os.path.exists(DST):
    shutil.rmtree(DST)
shutil.copytree('yeyeye_files', DST)
os.makedirs(f'{DST}/dp0/SYS/MECH', exist_ok=True)
with open(f'{DST}/dp0/SYS/MECH/ds.dat', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Plan A baseline ready: {DST}/dp0/SYS/MECH/ds.dat")
print("  - Original bonded contact, 0 offset")
print("  - Diagnostic block appended (max Uy, max SEQV, per-body stress)")
