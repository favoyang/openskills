# Native code, images, and dividers

Read when the parsed `insertions` list is nonempty.

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

For every native insertion, the exact placeholder and descending
`source_order` are authoritative. `block_index` and `after_text` are diagnostic
metadata only. When clicking a paragraph containing links, press `End` before
pasting an image to avoid inserting inside the link. Before previewing, require
no insertion placeholders remain and verify code count and spacing in preview.
