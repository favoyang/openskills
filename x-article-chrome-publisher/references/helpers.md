# Helper commands and conversion

## Scripts

- `scripts/parse_markdown.py <file>` emits structured JSON with `title`,
  `cover_image`, `content_images`, `code_blocks`, `dividers`, `blog_url`, `html`,
  `total_blocks`, `asset_root`, and `missing_images`. It rejects image paths
  outside the approved asset root and escapes raw HTML while limiting links to
  absolute HTTP(S) URLs.
- `--additional-asset-root <path>` narrowly allows generated images from a
  private per-run workspace without widening the article's primary asset root.
- `scripts/parse_markdown.py <file> --html-only` emits only the HTML body for
  rich-text clipboard paste.
- `scripts/copy_to_clipboard.py html --file <html-file>` copies rich HTML to
  the system clipboard. On macOS, run it through
  `uv run --with pyobjc-framework-Cocoa -- python3 ...` so `AppKit` is
  available even when the system Python lacks PyObjC.
- `scripts/copy_to_clipboard.py image <image> --quality 85` copies an image to
  the system clipboard, optionally compressing large uploads.
- `scripts/table_to_image.py <table.md> <table.png> --scale 2` converts a
  Markdown table fragment into a PNG.
- `scripts/temp_workspace.py create` prints a private, per-run directory in the
  platform's user-private temporary root. `cleanup <path>` removes only a
  direct managed child with the expected prefix and ownership marker.

Dependencies:

- Python 3.10+
- Prefer command-scoped dependencies with `uv run --with ... -- python3 ...`.
  Do not assume the system Python has optional packages installed.
- macOS image clipboard:
  `uv run --with pillow --with pyobjc-framework-Cocoa -- python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/copy_to_clipboard.py" image /path/to/image.png`
- macOS HTML clipboard:
  `uv run --with pyobjc-framework-Cocoa -- python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/copy_to_clipboard.py" html --file "$article_tmp/article.html"`
- Windows image clipboard:
  `uv run --with pillow --with pywin32 -- python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/copy_to_clipboard.py" image C:\path\to\image.png`
- Windows HTML clipboard:
  `uv run --with clip-util -- python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/copy_to_clipboard.py" html --file C:\path\to\article.html`
- Optional Mermaid rendering: use the pinned command-scoped package
  `npx --yes @mermaid-js/mermaid-cli@11.16.0`.

## Markdown Handling

Supported directly:

- H1 title extraction
- H2/H3 headings
- bold and italic text
- Markdown links
- blockquotes
- ordered and unordered lists
- fenced code blocks, extracted as `code_blocks` for native Insert > Code
  insertion because pasted code HTML is not reliable
- standalone Markdown images
- `---` dividers tracked for menu insertion
- `publish.blog.url` frontmatter, appended as a final cross-post paragraph

Tables and Mermaid diagrams should be converted to image files before parsing:

```bash
uv run --with pillow -- python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/table_to_image.py" "$article_tmp/table.md" "$article_tmp/table.png" --scale 2
npx --yes @mermaid-js/mermaid-cli@11.16.0 \
  -i "$article_tmp/diagram.mmd" -o "$article_tmp/diagram.png" -b white -s 2
```

Replace the original table or Mermaid block with a Markdown image reference
before running `parse_markdown.py`.
