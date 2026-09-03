# openskills

Public, Codex-specific agent skills maintained by
[Favo Yang](https://github.com/favoyang).

## Skills

- `branch-review-cli-loop` reviews complete branch diffs in fresh Codex CLI
  sessions and repeats after fixes until clean.
- `branch-review-subagent-loop` performs the same review loop with fresh,
  no-history Codex subagents.
- `personal-skill-maintenance` reviews recent Codex sessions and proposes
  evidence-backed skill improvements.
- `x-article-chrome-publisher` prepares Markdown as reviewable X Article drafts
  through Chrome automation and never publishes without confirmation.

## Install

Clone this repository, then link only the skills you want into
`~/.codex/skills`:

```bash
git clone https://github.com/favoyang/openskills.git
ln -s /path/to/openskills/personal-skill-maintenance \
  ~/.codex/skills/personal-skill-maintenance
```

These skills intentionally target Codex capabilities. They are not advertised
as portable cross-agent skills.

## Related standalone projects

- [Planrock](https://github.com/favoyang/planrock) provides saved Markdown
  plans and the `@favoyang/planrock` CLI.
- [Agentsnippet](https://github.com/favoyang/agentsnippet) expands reusable
  instruction snippets and publishes its own CLI.

Run `scripts/validate` before submitting changes.

## License

The repository is MIT licensed. Files with a more specific bundled license,
including `x-article-chrome-publisher/LICENSE`, retain that attribution.
