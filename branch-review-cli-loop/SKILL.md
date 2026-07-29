---
name: branch-review-cli-loop
description: Review the complete branch diff in fresh Codex CLI sessions, fix actionable findings, validate the fixes, and repeat until clean. Use before committing, pushing, creating, updating, approving, or merging a pull request; when repository instructions require an independent CLI review/fix loop; or when hosted review should not be the first review gate.
---

# Branch Review CLI Loop

Review the complete branch diff in a fresh `codex review` CLI session before
relying on hosted review.

## Workflow

1. Read repository instructions and identify the PR base branch, requested behavior, validation commands, and change scope.
2. Make intended new files visible to Git with `git add -N <exact-path>`. Do not broadly stage the worktree.
3. Run `<skill-dir>/scripts/run-branch-review.sh <base-branch>` from the repository root, resolving `<skill-dir>` from this skill's installed location. Each invocation starts a fresh `codex review` session.
4. Treat the result as full-diff code-review feedback. Prioritize correctness, regressions, missing tests, unsafe assumptions, deployment risk, and scope mismatches.
5. Verify each finding against the code. Fix every valid blocking finding in the same branch or worktree.
6. Run the relevant repository validation after fixes.
7. Start another fresh review with the same command. Repeat until it reports no blocking or actionable findings.
8. Only then commit, push, create/update the PR, or merge. Record the selected model, validation, and final review result.

Do not let a successful command exit code stand in for a clean review; `codex review` can exit successfully while reporting findings. Read its final review text.

## Model Selection

The runner tries the newest configured candidate first and falls back only when the model is unavailable, unsupported, or requires a newer Codex version. The default order is:

`gpt-5.6-sol,gpt-5.5,gpt-5.4`

Override it when newer models become available:

```bash
BRANCH_REVIEW_MODELS="gpt-newest,gpt-5.6-sol,gpt-5.5" \
  <skill-dir>/scripts/run-branch-review.sh main
```

Do not fall back merely because a review finds bugs or a command fails for a repository-specific reason.

## Review Boundary

- Pass the base branch as the runner's first positional argument, for example `<skill-dir>/scripts/run-branch-review.sh main`, to review the full branch diff including relevant working-tree changes.
- The runner stops when untracked files exist because Git diff review cannot see them. Mark intended new files with `git add -N <exact-path>` and ignore unrelated generated files explicitly.
- Keep the reviewer independent: do not pre-seed it with expected findings or proposed fixes.
- Use GitHub review feedback after the local loop as an additional signal, not as a replacement.
- If no candidate model can run, stop and report every attempted model and the final compatibility error.
