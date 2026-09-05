---
name: x-article-chrome-publisher
description: "Prepare Markdown as a reviewable X Article draft through Chrome, preserving rich text and native media. Final publication requires explicit user confirmation."
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

## Choose the work

For draft creation or editing, follow [draft workflow](references/draft-workflow.md).
It covers private temporary files, parsing, approved asset paths, editor input,
preview, and cleanup. Use the supported Chrome skill for browser setup and
interaction. An authorized draft request permits correcting preparation and
formatting failures through a reviewable draft without asking at each step;
account uncertainty, unavailable assets, and final publication retain the
boundaries above.

- For tables, Mermaid conversion, optional dependencies, or helper options,
  read [helpers](references/helpers.md).
- For nonempty parsed `insertions`, read
  [native insertions](references/native-insertions.md) before inserting them.
- For helper changes or diagnostics, use
  [helper validation](references/helper-validation.md).

## Completion

A draft is ready when the intended account, title, cover, rich body, links,
native insertions, and any cross-post URL are verified in preview. Resolve
missing or duplicate placeholders and code spacing defects before reporting
success. Report any blocked validation honestly. Remove only the recorded
managed temporary workspace on success, failure, or cancellation; report its
path if interrupted cleanup leaves it behind. Stop at the reviewable draft
unless explicit final-publication confirmation is established.
