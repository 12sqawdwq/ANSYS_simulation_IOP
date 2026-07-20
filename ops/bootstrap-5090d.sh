#!/usr/bin/env bash
set -euo pipefail
origin_dir=/home/xuanyu/PROJECT/ziyu/git/blueknow-simulation.git
worktree=/home/xuanyu/PROJECT/ziyu/blueknow/simulation
mkdir -p "$(dirname "$origin_dir")" "$(dirname "$worktree")"
if [[ ! -d "$origin_dir" ]]; then git init --bare --initial-branch=main "$origin_dir"; fi
git -C "$origin_dir" config uploadpack.allowFilter true
git -C "$origin_dir" config uploadpack.allowAnySHA1InWant true
if [[ ! -d "$worktree/.git" ]]; then git clone "$origin_dir" "$worktree"; fi
git -C "$worktree" config pull.ff only
git -C "$worktree" pull --ff-only
