---
name: git-workflow
description: Git workflow helper. Use for commits, branches, rebases and release tagging.
---

# Git Workflow

## Branching

```bash
git checkout -b feature/my-feature
git commit -m "feat: add my feature"
git rebase main
```

## Releases

- Tag: `git tag -a v1.2.0 -m "release 1.2.0"`
- Push: `git push origin main --follow-tags`
- Undo last commit keeping changes: `git reset --soft HEAD~1`
