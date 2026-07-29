---
name: x-article-chrome-publisher
description: Publish Markdown files as X Articles drafts through Chrome automation in Codex Apps. Use when the user asks to publish, post, prepare, draft, or convert a Markdown article for X/Twitter Articles through the browser editor, especially when the article contains headings, links, lists, images, dividers, tables, or Mermaid diagrams and should preserve rich-text formatting.
---

# X Article Chrome Publisher

Prepare a Markdown article for X Articles, open the X Articles editor, fill the
draft through Chrome, and stop before final publication unless the user gives an
explicit publish confirmation.

This is the Chrome/browser-editor implementation. It is currently validated for
Codex Apps with the Codex Chrome Extension connected. It is not a Codex CLI
skill today because the CLI environment cannot drive the connected Chrome
extension flow reliably. For an implementation that posts through X's API, use a
separate API-focused skill with a distinct name.

## Core Rules

- Never click the final Publish/Post button without explicit user confirmation.
- Use the first Markdown image as the cover image.
- Use the first H1 as the X Article title and remove it from the pasted body.
- Paste rich text from generated HTML through the browser clipboard or system
  clipboard. Treat rich-clipboard failure as a blocker for public/live
  publishing unless the user explicitly accepts degraded plain text. Do not
  manually type Markdown or plain text with blank lines into the editor; X can
  expand those lines into excessive visual spacing.
- Do not paste fenced code blocks as `<pre><code>` HTML. X flattens pasted code
  HTML into normal article text. Replace code blocks with temporary placeholders
  in the initial rich-text paste, then insert each block through X's native
  Insert > Code dialog.
- Do not leave an empty DraftJS paragraph before a native code block. It renders
  as unnecessary vertical spacing. Remove insertion-anchor paragraphs after all
  code blocks are present, then verify that no empty predecessor remains before
  a native code block.
- When source frontmatter includes `publish.blog.url`, include the generated
  final cross-post paragraph in the X Article body and verify the blog URL in
  preview before publication.
- Insert native code, content images, and dividers after the body paste from
  highest `source_order` to lowest, replacing each deterministic placeholder
  so earlier positions do not shift.
- If Chrome is not running, launch it before browser validation.
- If X asks for login, pause and ask the user to log in manually.
- Before creating or editing a draft, verify the visible X account is the
  intended publishing account. If the intended account is not already
  established by the current request, ask the user to confirm it.
- Clipboard helpers replace the current system clipboard. Warn the user before
  the first clipboard write and do not copy unrelated sensitive content during
  the workflow.

## Quick Workflow

1. Resolve the Markdown file path and its containing directory. Bundled helpers
   and examples must always be addressed through the installed skill directory
   under `${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher`, never
   relative to the caller's working directory.
2. Create one private workspace for all generated files, record the printed
   path as `article_tmp`, and use it until cleanup. The helper uses a mode-0700
   directory on POSIX and the current user's `%LOCALAPPDATA%\Temp` on Windows:

   ```bash
   article_tmp="$(python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/temp_workspace.py" create)"
   printf 'Article workspace: %s\n' "$article_tmp"
   ```

   Optionally convert tables or Mermaid diagrams to images inside that
   workspace and replace them in the Markdown before parsing. Leave fenced code
   blocks in Markdown; they are extracted and inserted through X's native Code
   dialog. Use the generated files' canonical paths in Markdown and approve
   only this exact workspace as the additional asset root. Never use fixed
   names directly under a shared temporary directory.
3. Parse the article:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/parse_markdown.py" /path/to/article.md \
     --additional-asset-root "$article_tmp" > "$article_tmp/article.json"
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/parse_markdown.py" /path/to/article.md \
     --additional-asset-root "$article_tmp" --html-only > "$article_tmp/article.html"
   ```

   Images are restricted to the Markdown file's directory by default. If the
   article intentionally uses a wider asset tree, pass its narrowest common
   parent with `--asset-root /path/to/approved-assets`.
4. Inspect `$article_tmp/article.json` for `missing_images`, `asset_root`, and every
   canonical image path. Stop for missing images or paths outside the approved
   asset root. Confirm the listed files are intended article assets before
   opening X; never substitute a same-named file from another directory.
5. Open Chrome and navigate to `https://x.com/compose/articles`.
6. Create a new article draft if the page shows the article list.
7. Upload `cover_image` with the editor's visible `Choose File` cover control.
   If X opens the media editor, click `Apply` after the image preview appears.
8. Fill the title from `title`.
9. Copy the generated HTML and paste it into the body editor:

   ```bash
   uv run --with pyobjc-framework-Cocoa -- \
     python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/copy_to_clipboard.py" html --file "$article_tmp/article.html"
   ```

   When Chrome browser automation exposes `tab.clipboard.write`, prefer writing
   both `text/html` and compact `text/plain` entries directly to the browser
   clipboard before pressing `Meta+V`. If neither rich path works, stop before
   public publication and report the blocker. Plain-text fallback is acceptable
   only for a draft or after explicit user approval of degraded formatting; it
   should use single newlines only, not blank lines between every block.

10. Process the combined `insertions` list from highest `source_order` to
    lowest. Every item contains an exact placeholder. Replace it according to
    `kind`:

    - `code`: click its `[[CODE_BLOCK_NN]]` placeholder, open Insert > Code,
      paste the exact `code`, preview if useful, and click Insert. Delete the
      placeholder only after the native block is present. Common language
      mappings: `sh`/`bash`/`zsh` -> Shell, `md`/`markdown` -> Markdown, and
      `text` -> Plain Text when available or leave the language blank.
    - `image`: click its `[[IMAGE_NN]]` placeholder and copy the exact
      canonical `path`:

      ```bash
      uv run --with pillow --with pyobjc-framework-Cocoa -- \
        python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/copy_to_clipboard.py" image /path/to/image.png --quality 85
      ```

      Paste with `Meta+V`, wait for upload completion, then remove the
      placeholder only after the image is present.
    - `divider`: click its `[[DIVIDER_NN]]` placeholder, insert a divider
      through the X editor Insert menu, then remove the placeholder. Do not
      rely on pasted `<hr>` HTML.

    If any placeholder is missing, duplicated, or cannot be replaced at its
    source position, stop and rebuild the body instead of guessing from a
    shared `block_index`.

    X may leave the placeholder paragraph empty immediately before the native
    code block. Remove that paragraph before previewing: click its inner block,
    then send `Backspace` to the DraftJS `[contenteditable="true"]` root. Sending
    `Backspace` only to the clicked inner block can appear to succeed while
    leaving the paragraph in the editor state. Work from bottom to top so block
    positions stay stable.

    After cleanup, evaluate the editor and require both conditions:

    - the number of native code blocks matches `code_blocks.length`
    - no native code block is immediately preceded by a `[data-block="true"]`
      paragraph whose text is empty after removing zero-width characters and
      trimming whitespace

    Identify native code blocks by their code content and `Edit block` control,
    then inspect the preceding editor block. Ignore unrelated DraftJS terminal
    or sentinel blocks; the spacing defect is specifically an empty predecessor
    of a native code block.

11. Preview the article, report that the draft is ready, and ask the user to
    review and publish manually.
12. Before ending the workflow for success, failure, or cancellation, remove
    only the recorded managed workspace:

    ```bash
    python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/temp_workspace.py" cleanup "$article_tmp"
    ```

    If cleanup cannot run because the task is interrupted, the directory and
    marker remain private to the current user; report the recorded path so it
    can be cleaned later.

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

## Browser Notes

Use the active Chrome session when possible. The X Articles page often opens to
a drafts/articles list; click the create/new article control before looking for
title or body fields.

Avoid excessive snapshots and fixed waits. Browser actions usually return the
page state needed for the next step. Use explicit waits only for page loading,
login completion, and media upload completion.

For cover upload, prefer the visible `Choose File` button shown inside the
cover placeholder over clicking a hidden `input[type=file]`. After `setFiles`,
wait for X's media editor preview and click `Apply`; verify that the placeholder
text is gone and the draft contains a media image before continuing.

After pasting the body, verify the editor text before inserting media. A good
smoke-test signal is that `innerText` contains the expected headings and list
items without repeated blank lines. For live/public publication, also preview
the article and verify that paragraphs, links, and lists render as rich content
before clicking Publish. If spacing is wrong, replace the body with a compact
rich-text paste; do not recover by typing a multi-paragraph plain-text body line
by line.

For code blocks, do not rely on pasted `<pre><code>` HTML. The reliable path is
to paste the body with code placeholders, verify the placeholder count matches
`code_blocks.length`, and insert native code blocks from bottom to top. Before
previewing, verify that no `[[CODE_BLOCK_` placeholders remain, no native code
block has an empty DraftJS predecessor, and the preview exposes exactly
`code_blocks.length` code elements, ideally with X's copy controls. Do not fail
on unrelated terminal or sentinel blocks. Treat an empty paragraph immediately
before a code block as a failed spacing check, not harmless editor structure.

For every native insertion, the exact placeholder and descending
`source_order` are authoritative. `block_index` and `after_text` are diagnostic
metadata for human verification only; never use them to guess a location when
the placeholder is missing. When clicking a paragraph that contains links,
press `End` before pasting an image so the cursor moves to the paragraph end
instead of inside the link.

If browser automation reports that the browser is already in use, use the
existing tab/session when possible. If no usable Chrome session exists, launch
Chrome and retry navigation.

## Validation

Before live browser work, validate parsing without posting:

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
