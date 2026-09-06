# Optional reviewer preferences

Requires Python 3.11+ only when using the packaged resolver. Read native agent
TOML from `$CODEX_HOME/agents/` (default `~/.codex/agents/`) and the explicitly
selected repository's `.codex/agents/`. Resolve from the actual review worktree,
not the dispatcher directory. No parent-directory search is performed.

```sh
python3 <skill-dir>/scripts/resolve_roles.py --project <repo-root> --role reviewer
```

Roles are identified by the TOML `name`, including custom filenames. Files need
native `name`, `description`, and `developer_instructions` strings. Only `model`
and `model_reasoning_effort` are used by this adapter; it does not load native
agent instructions, permissions, tools, or other configuration layers.

Precedence is explicit user model (plus its explicit effort), then project role,
then personal role, then native defaults. An explicit model without an explicit
effort omits effort and leaves its meaning to the current native interface; do
not mix in an effort from a different role model or claim a specific effective
effort without evidence. Check any inherited effort against the selected model
when the interface documents inheritance.
An explicit effort alone replaces the role effort. Pass explicit choices using
`--model` and/or `--effort`. Project profiles replace personal profiles as a unit.

Use `subagentOverrides` only after comparing model and effort with the current
spawn tool's supported choices. Cached catalog evidence is advisory, may be
stale, and does not prove successful execution. A missing role is optional:
omit model and effort to inherit parent settings. An invalid profile, duplicate
name, unavailable model/effort, or resolver failure must be reported; do not
silently claim it was honored. A current native tool can disprove a stale cache
warning; explain that evidence before passing explicit values. Otherwise resolve
the problem or obtain a valid explicit user choice before spawning.

If Python is unavailable, check whether relevant native role files exist before
continuing without overrides. No role files means the normal inherited fallback;
existing files mean configuration remains unresolved. Never read unrelated
configuration or expose arbitrary TOML contents to diagnose a role.

[Official native agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
describes named native configuration layers. Some desktop/subagent APIs expose
only explicit model and effort fields and no named-agent selector. A matching
`task_name` is not proof that a native role loaded. Prefer an available native
selector only when its effective model and effort can be verified; otherwise
use this narrow adapter and retain fresh no-history review prompts.
