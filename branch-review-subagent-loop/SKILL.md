---
name: branch-review-subagent-loop
description: "Review the complete Git branch and working-tree diff with fresh Codex subagents, fixing verified findings until clean. Use when requested or required as an independent review gate."
---

# Branch Review Subagent Loop

Review independently; keep all repository changes in the parent task.

## Workflow

1. Read the repository instructions. Identify the base branch, requested
   behavior, intended scope, and validation commands.
2. Run `git status --short --untracked-files=all`. Mark each intended untracked
   file with `git add -N -- <exact-file-path>` so the reviewer can see it. Never
   pass a directory or broadly stage the worktree. Resolve any remaining
   untracked path before review.
3. Start a new subagent with `fork_turns="none"` and no model override. If fresh
   delegation is unavailable, stop; do not fall back to `/review`, `codex
   review`, `codex exec`, another `codex` command, or a review script.
4. Give the reviewer the repository root, base branch, requested behavior, and
   this prompt:

```text
Review only; do not modify files, the index, or repository state.

Review the complete change against <base> in <repo-root>, including committed,
staged, unstaged, and intent-to-add changes. Establish the merge base so
base-only changes are excluded. Read the repository instructions. Focus on
correctness, regressions, security, missing tests, unsafe assumptions, and
scope mismatches.

Return severity-ordered actionable findings with file and line, evidence,
impact, and remediation. Return CLEAN if none exist. State what you inspected
and any coverage limits.
```

5. Verify each finding. Fix valid findings and run validation in the parent
   task.
6. Start another fresh no-history reviewer with the same neutral prompt. Repeat
   until it returns `CLEAN` with complete coverage.

Do not seed reviewers with expected findings, prior feedback, or fixes. Treat
missing coverage or ambiguous output as a failed pass. Use hosted review only
as an additional signal.
