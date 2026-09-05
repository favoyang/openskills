# Prepare and fill a draft

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

10. When `insertions` is nonempty, read
    [native insertions](native-insertions.md) and complete them before preview.

11. Preview the article and verify title, cover, rich paragraphs, links, lists,
    and any generated cross-post URL. Correct formatting failures within the
    authorized draft workflow. Report the reviewable draft; final publication
    requires explicit user confirmation.
12. Before ending the workflow for success, failure, or cancellation, remove
    only the recorded managed workspace:

    ```bash
    python3 "${CODEX_HOME:-$HOME/.codex}/skills/x-article-chrome-publisher/scripts/temp_workspace.py" cleanup "$article_tmp"
    ```

    If cleanup cannot run because the task is interrupted, the directory and
    marker remain private to the current user; report the recorded path so it
    can be cleaned later.

For cover upload, verify that the placeholder is gone and the draft contains
the intended image after applying the media preview. After body paste, verify
expected headings and list items without repeated blank lines. Correct spacing
with a compact rich-text paste rather than typing the body line by line.
