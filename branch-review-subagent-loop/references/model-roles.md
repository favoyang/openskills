# Optional reviewer preferences

Requires Python 3.11+ only when using the packaged resolver. Read native agent
TOML only from the global `$CODEX_HOME/agents/` directory (default
`~/.codex/agents/`). Repository-local agent profiles are not read.

```sh
python3 <skill-dir>/scripts/resolve_roles.py --role reviewer
```

Roles are identified by the TOML `name`, including custom filenames. Files need
native `name`, `description`, and `developer_instructions` strings. Only `model`
and `model_reasoning_effort` are used by this adapter; it does not load native
agent instructions, permissions, tools, or other configuration layers.

Precedence is explicit user model (plus its explicit effort), then global role,
then native defaults. An explicit model without an explicit
effort omits effort and leaves its meaning to the current native interface; do
not mix in an effort from a different role model or claim a specific effective
effort without evidence. Check any inherited effort against the selected model
when the interface documents inheritance.
An explicit effort alone replaces the role effort. Pass explicit choices using
`--model` and/or `--effort`.

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

Some desktop/subagent APIs expose a named-agent selector, but its configuration
may include repository-local layers or settings beyond model and effort. Do not
use a named selector for this workflow. Use this narrow adapter's explicit model
and effort overrides and retain fresh no-history review prompts.
