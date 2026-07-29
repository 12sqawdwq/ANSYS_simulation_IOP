#!/usr/bin/env bash
# Mirror the authoritative internal main branch to GitHub without touching the worktree.
set -euo pipefail

internal_remote=${INTERNAL_REMOTE:-origin}
github_remote=${GITHUB_REMOTE:-github}
branch=${SYNC_BRANCH:-main}

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

if ! git remote get-url "$internal_remote" >/dev/null 2>&1; then
  echo "missing internal remote: $internal_remote" >&2
  exit 2
fi
if ! git remote get-url "$github_remote" >/dev/null 2>&1; then
  echo "missing GitHub remote: $github_remote" >&2
  exit 2
fi

git fetch "$internal_remote" "$branch"
internal_ref="refs/remotes/$internal_remote/$branch"
internal_sha=$(git rev-parse "$internal_ref")
github_sha=$(git ls-remote --heads "$github_remote" "refs/heads/$branch" | awk '{print $1}')

if [[ "$github_sha" != "$internal_sha" ]]; then
  git push "$github_remote" "$internal_ref:refs/heads/$branch"
fi

verified_sha=$(git ls-remote --heads "$github_remote" "refs/heads/$branch" | awk '{print $1}')
if [[ "$verified_sha" != "$internal_sha" ]]; then
  echo "GitHub verification failed: internal=$internal_sha github=$verified_sha" >&2
  exit 1
fi

printf 'synchronized branch=%s internal=%s github=%s\n' \
  "$branch" "$internal_sha" "$verified_sha"
