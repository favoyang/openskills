## Validation

When modifying helpers or diagnosing parsing/rendering failures, run relevant
checks below. Ordinary draft preparation parses and verifies the actual article;
it does not require rerunning the helper suite. These local checks do not post:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/parse_markdown.py" \
  "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/examples/article.md"
python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/parse_markdown.py" \
  "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/examples/article.md" --html-only
python3 -m unittest discover \
  -s "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/tests" -v
article_tmp="$(python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/temp_workspace.py" create)"
uv run --with pillow -- \
  python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/table_to_image.py" \
  "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/examples/table.md" \
  "$article_tmp/x-table.png"
python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/temp_workspace.py" cleanup "$article_tmp"
```

Live validation should stop at a reviewable draft unless the user explicitly
confirms final publication.
