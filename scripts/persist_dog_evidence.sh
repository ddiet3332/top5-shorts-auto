#!/usr/bin/env bash
# Publish the current attempt to the evidence branch of this checkout's origin.
set -euo pipefail
archive="$1"
target="$2"
record_tool="$3"
branch=top5-review-evidence
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
if git ls-remote --exit-code --heads origin "$branch" >/dev/null; then
  git fetch --no-tags origin "refs/heads/$branch"
  git worktree add --detach "$target" FETCH_HEAD
else
  status=$?
  [[ "$status" == 2 ]]
  git worktree add --detach "$target" HEAD
  git -C "$target" switch --orphan "$branch"
fi
python3 "$record_tool" record "$archive" "$target/review"
git -C "$target" add -- review
if ! git -C "$target" diff --cached --quiet; then
  git -C "$target" commit -m "Record dog production evidence"
  git -C "$target" push origin "HEAD:refs/heads/$branch"
fi
