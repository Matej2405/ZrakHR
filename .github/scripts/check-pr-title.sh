#!/usr/bin/env bash
# Provjerava prati li naslov pull requesta Conventional Commits, npr. "feat: karta postaja"
# ili "fix(api): prazan odgovor". Naslov se čita iz prvog argumenta ili varijable PR_TITLE.
# Upotreba: check-pr-title.sh ["naslov"]
set -euo pipefail

title="${1:-${PR_TITLE:-}}"
types='feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert'
pattern="^(${types})(\([a-z0-9._-]+\))?!?: [^ ].*$"

if [[ "$title" =~ $pattern ]]; then
  echo "Naslov PR-a prati Conventional Commits: $title"
else
  echo "::error title=Naslov PR-a::\"$title\" ne prati Conventional Commits. Primjer: \"feat: karta postaja\". Dopušteni tipovi: ${types//|/, }."
  exit 1
fi
