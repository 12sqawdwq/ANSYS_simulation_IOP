#!/usr/bin/env bash
set -euo pipefail
origin=ssh://xuanyu@113.44.57.56:8025/home/xuanyu/PROJECT/ziyu/git/blueknow-simulation.git
target=/home/ziyu/PROJECT/blueknow/simulation
mkdir -p "$(dirname "$target")"
if [[ ! -d "$target/.git" ]]; then rmdir "$target" 2>/dev/null || true; git clone --filter=blob:none --no-checkout "$origin" "$target"; fi
git -C "$target" config pull.ff only
git -C "$target" sparse-checkout init --cone
git -C "$target" sparse-checkout set baseline offset thick docs results/summary
git -C "$target" checkout main
git -C "$target" pull --ff-only
