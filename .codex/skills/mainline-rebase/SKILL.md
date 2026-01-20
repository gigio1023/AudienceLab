---
name: mainline-rebase
description: Keep work on the main branch only, rebase onto origin/main, resolve conflicts safely, and push directly to main. Use whenever the hackathon workflow forbids feature branches or requires conflict resolution.
---

# Mainline Rebase Workflow

## Golden rules

- Stay on `main` only (no feature branches).
- Use `git rebase origin/main` to resolve upstream changes.
- Do not force-push; prefer clean, fast-forward pushes.

## Standard flow

```bash
# Confirm branch
git branch --show-current

# Inspect status
git status -sb

# Update upstream refs
git fetch origin

# Rebase on latest main
git rebase origin/main
```

Ensure a clean working tree before rebasing. If there are local changes, commit them or use:

```bash
git stash push -u -m "pre-rebase"
# ...rebase...
git stash pop
```

## If conflicts happen

1. Open conflicted files and resolve manually.
2. `git add <file>` for each resolved file.
3. Continue: `git rebase --continue`.
4. If the rebase becomes unclear, stop and ask for guidance instead of using destructive commands.

## Commit + push

```bash
git add -A
git commit -m "<message>"
git push origin main
```

## If push is rejected

```bash
git fetch origin
git rebase origin/main
git push origin main
```
