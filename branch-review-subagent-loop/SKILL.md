---
name: branch-review-subagent-loop
description: "Review the complete Git branch and working-tree diff with a fresh read-only Codex subagent. Use when requested or required as an independent review gate; return findings or CLEAN without modifying the repository."
---

# Branch Review Subagent Loop

Review independently without modifying the repository. Each invocation uses a
fresh reviewer and returns findings or `CLEAN`. The invoking task owns finding
verification, fixes, validation, and any later review invocation.

## Workflow

1. Read the repository instructions. Identify the base branch, requested
   behavior, intended scope, and validation commands.
2. Run `git status --short --untracked-files=all`. Record intended untracked
   files by exact path and resolve unexpected untracked paths before review. Do
   not change the index.
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
staged, and unstaged changes plus these intended untracked files:
<untracked-paths-or-none>. Read those files directly without changing the
index. Establish the merge base so base-only changes are excluded. Read the
repository instructions. Focus on correctness, regressions, security, missing
tests, unsafe assumptions, and scope mismatches.

Return severity-ordered actionable findings with file and line, evidence,
impact, and remediation. Return CLEAN if none exist. State what you inspected
and any coverage limits.
```

5. Return the reviewer's findings or `CLEAN` result to the invoking task. Do not
   fix findings, run mutating commands, or coordinate another writer.

Do not seed reviewers with expected findings, prior feedback, or fixes. Treat
missing coverage or ambiguous output as a failed pass. Use hosted review only
as an additional signal. If invoked again after changes, repeat the entire
workflow with another fresh reviewer.
