#!/usr/bin/env bash
set -euo pipefail
git fsck --full
git diff --check
if git ls-files | grep -E '\.(rst|rdb|db|mechdb|full|esav|emat|mntr|gst|DSP|cnd|ldhi|tar|tgz|zip)$'; then exit 1; fi
printf 'HEAD=%s\n' "$(git rev-parse HEAD)"
printf 'origin/main=%s\n' "$(git rev-parse origin/main)"
