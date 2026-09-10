---
name: branch-review-subagent-loop
description: "Review the complete Git branch and working-tree diff with fresh Codex subagents, fixing verified findings until clean. Use when requested or required as an independent review gate."
---

# Branch Review Subagent Loop

Review independently. The invoking task owns the review gate and normally makes
verified fixes itself. When its governing workflow requires a separate writer,
use the delegated-writer option below without transferring review ownership.

## Workflow

1. Read the repository instructions. Identify the base branch, requested
   behavior, intended scope, and validation commands.
2. Run `git status --short --untracked-files=all`. Mark each intended untracked
   file with `git add -N -- <exact-file-path>` so the reviewer can see it. Never
   pass a directory or broadly stage the worktree. Resolve any remaining
   untracked path before review.
3. Resolve the optional `reviewer` model/effort using the packaged
   [role preferences](references/model-roles.md) instructions. Preserve explicit
   user choices. Missing roles mean omit overrides and inherit parent settings;
   invalid or unavailable configuration must be surfaced before review.
   Start a new subagent with `fork_turns="none"` and the resolved, supported
   overrides, if any. If fresh
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

5. Verify each finding. By default, fix valid findings and run validation in
   the invoking task. When required by the governing workflow, the invoking
   task may instead assign verified fixes to a separate writer only when:
   - the reviewer has ended and remains read-only;
   - the writer receives the bounded findings, exact repository/worktree,
     owned paths, and required validation;
   - the writer has exclusive write ownership and is told not to revert
     unrelated changes;
   - the invoking task establishes that the writer has ended before accepting
     the patch or starting another reviewer; and
   - the invoking task verifies the resulting diff and validation evidence.

   A timeout or uncertain spawn response is not evidence that a writer stopped.
   If exclusive ownership cannot be established, stop the review loop. This
   option does not let the reviewer edit or reuse the reviewer as the writer.
6. Start another fresh no-history reviewer with the same neutral prompt. Repeat
   until it returns `CLEAN` with complete coverage.

Do not seed reviewers with expected findings, prior feedback, or fixes. Treat
missing coverage or ambiguous output as a failed pass. Use hosted review only
as an additional signal.
