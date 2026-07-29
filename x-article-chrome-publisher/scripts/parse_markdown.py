#!/usr/bin/env python3
"""
Parse Markdown for X Articles publishing.

Extracts:
- Title (from first H1/H2 or first line)
- Cover image (first image)
- Content images with block index for precise positioning
- Dividers (---) with block index for menu insertion
- Fenced code blocks with language and block index for native insertion
- Blog cross-post URL from frontmatter, when present
- HTML content (images and dividers stripped)

Usage:
    python3 parse_markdown.py <markdown_file> [--output json|html]

Output (JSON):
{
    "title": "Article Title",
    "cover_image": "/path/to/cover.jpg",
    "content_images": [
        {"path": "/path/to/img.jpg", "block_index": 3, "after_text": "context..."},
        ...
    ],
    "dividers": [
        {"block_index": 7, "after_text": "context..."},
        ...
    ],
    "code_blocks": [
        {"language": "sh", "code": "npm test", "block_index": 8, "after_text": "context..."},
        ...
    ],
    "blog_url": "https://example.com/post/",
    "html": "<p>Content...</p><h2>Section</h2>...",
    "total_blocks": 25
}

The block_index indicates which block element (0-indexed) the image/divider/code block should follow.
This allows precise positioning without relying on text matching.

Note: Dividers must be inserted via X Articles' Insert > Divider menu, not HTML <hr> tags.
Note: Code blocks must be inserted via X Articles' Insert > Code menu, not pasted as HTML.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path


class UnsafeAssetPath(ValueError):
    """Raised when a Markdown image resolves outside the approved asset root."""


RESERVED_PLACEHOLDER_PATTERN = re.compile(
    r'\[\[(?:CODE_BLOCK|IMAGE|DIVIDER)_\d+\]\]'
)
RESERVED_SENTINEL_PATTERN = re.compile(
    r'___(?:DIVIDER|CODE_BLOCK_(?:START|CONTENT|END))___'
)


def markdown_destination(raw: str) -> str:
    """Extract a URL/path from a balanced Markdown destination and optional title."""
    value = raw.strip()
    if value.startswith("&lt;"):
        end = value.find("&gt;", 4)
        if end == -1:
            return value
        return unescape_markdown_punctuation(value[4:end])
    if value.startswith("<"):
        end = value.find(">", 1)
        if end == -1:
            return value
        return unescape_markdown_punctuation(value[1:end])

    depth = 0
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char.isspace() and depth == 0:
            return unescape_markdown_punctuation(value[:index])
    return unescape_markdown_punctuation(value)


def unescape_markdown_punctuation(value: str) -> str:
    """Remove Markdown escapes before ASCII punctuation."""
    result = []
    index = 0
    while index < len(value):
        if (
            value[index] == "\\"
            and index + 1 < len(value)
            and 33 <= ord(value[index + 1]) <= 126
            and not value[index + 1].isalnum()
        ):
            result.append(value[index + 1])
            index += 2
            continue
        result.append(value[index])
        index += 1
    return ''.join(result)


def markdown_label(raw: str) -> str:
    """Unescape punctuation in a Markdown label."""
    return re.sub(r'\\([\\[\]])', r'\1', raw)


def parse_markdown_link_at(text: str, start: int, image: bool = False):
    """Parse one inline Markdown link/image with balanced destination parentheses."""
    prefix = "![" if image else "["
    if not text.startswith(prefix, start):
        return None

    label_start = start + len(prefix)
    label_depth = 1
    escaped = False
    label_end = None
    index = label_start
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "[":
            label_depth += 1
        elif char == "]":
            label_depth -= 1
            if label_depth == 0:
                label_end = index
                break
        index += 1

    if (
        label_end is None
        or label_end + 1 >= len(text)
        or text[label_end + 1] != "("
    ):
        return None

    destination_start = label_end + 2
    depth = 1
    escaped = False
    quote = None
    title_separator_seen = False
    in_angle = (
        text.startswith("<", destination_start)
        or text.startswith("&lt;", destination_start)
    )
    index = destination_start
    while index < len(text):
        if in_angle and text.startswith("&gt;", index):
            in_angle = False
            index += 4
            continue
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif in_angle:
            if char == ">":
                in_angle = False
        elif quote:
            if char == quote:
                quote = None
        elif char.isspace() and depth == 1:
            title_separator_seen = True
        elif char in {'"', "'"} and title_separator_seen:
            quote = char
        elif char == "(":
            title_separator_seen = False
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return {
                    "label": markdown_label(text[label_start:label_end]),
                    "destination": markdown_destination(
                        text[destination_start:index]
                    ),
                    "end": index + 1,
                }
        elif not char.isspace():
            title_separator_seen = False
        index += 1
    return None


def parse_image_block(block: str):
    """Parse a standalone Markdown image block."""
    parsed = parse_markdown_link_at(block, 0, image=True)
    if parsed is None or parsed["end"] != len(block):
        return None
    return parsed


def fence_marker(line: str):
    """Return fence character, run length, and suffix for a Markdown fence."""
    match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
    if match is None:
        return None
    run = match.group(1)
    return run[0], len(run), match.group(2)


def resolve_image_path(
    reference: str,
    base_path: Path,
    asset_roots: tuple[Path, ...],
) -> tuple[str, bool]:
    """Resolve a local image while enforcing containment in approved roots."""
    decoded = urllib.parse.unquote(reference)
    candidate = Path(decoded).expanduser()
    if not candidate.is_absolute():
        candidate = base_path / candidate

    resolved = candidate.resolve()
    approved_roots = tuple(root.resolve() for root in asset_roots)
    if not any(
        resolved == root or resolved.is_relative_to(root)
        for root in approved_roots
    ):
        raise UnsafeAssetPath(
            f"Image path resolves outside approved asset roots "
            f"{[str(root) for root in approved_roots]}: "
            f"'{reference}' -> '{resolved}'"
        )

    exists = resolved.is_file()
    if not exists:
        print(f"[parse_markdown] WARNING: Image not found: '{resolved}'", file=sys.stderr)
    return str(resolved), exists


def split_into_blocks(markdown: str) -> list[str]:
    """Split markdown into logical blocks (paragraphs, headers, quotes, code blocks, etc.)."""
    blocks = []
    current_block = []
    fence_character = None
    fence_length = 0
    code_block_lines = []
    code_block_language = ""

    lines = markdown.split('\n')

    for line in lines:
        stripped = line.strip()

        marker = fence_marker(line)

        # Handle code block boundaries.
        if fence_character is not None:
            if (
                marker is not None
                and marker[0] == fence_character
                and marker[1] >= fence_length
                and not marker[2].strip()
            ):
                # End of code block
                fence_character = None
                fence_length = 0
                blocks.append(
                    '___CODE_BLOCK_START___'
                    + code_block_language
                    + '\n___CODE_BLOCK_CONTENT___\n'
                    + '\n'.join(code_block_lines)
                    + '___CODE_BLOCK_END___'
                )
                code_block_lines = []
                code_block_language = ""
            else:
                code_block_lines.append(line)
            continue

        if marker is not None:
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            fence_character = marker[0]
            fence_length = marker[1]
            code_block_language = marker[2].strip()
            continue

        # Empty line signals end of block
        if not stripped:
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            continue

        # Horizontal rule (divider) is its own block
        if re.match(r'^---+$', stripped):
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            blocks.append('___DIVIDER___')
            continue

        # Headers, blockquotes are their own blocks
        if stripped.startswith(('#', '>')):
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            blocks.append(stripped)
            continue

        # Image on its own line is its own block
        if parse_image_block(stripped) is not None:
            if current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
            blocks.append(stripped)
            continue

        current_block.append(line)

    if current_block:
        blocks.append('\n'.join(current_block))

    # Handle unclosed code block
    if code_block_lines:
        blocks.append(
            '___CODE_BLOCK_START___'
            + code_block_language
            + '\n___CODE_BLOCK_CONTENT___\n'
            + '\n'.join(code_block_lines)
            + '___CODE_BLOCK_END___'
        )

    return blocks


def extract_insert_blocks(
    markdown: str,
    base_path: Path,
    asset_roots: tuple[Path, ...],
) -> tuple[list[dict], list[dict], list[dict], str, int]:
    """Extract images, dividers, and code blocks with their block index positions.

    Returns:
        (image_list, divider_list, code_block_list, clean_markdown, total_blocks)
    """
    blocks = split_into_blocks(markdown)
    images = []
    dividers = []
    code_blocks = []
    clean_blocks = []

    code_pattern = re.compile(
        r'^___CODE_BLOCK_START___(.*?)\n___CODE_BLOCK_CONTENT___\n(.*?)___CODE_BLOCK_END___$',
        re.DOTALL,
    )

    for i, block in enumerate(blocks):
        block_stripped = block.strip()

        # Check for divider
        if block_stripped == '___DIVIDER___':
            block_index = len(clean_blocks)
            placeholder = f"[[DIVIDER_{len(dividers) + 1:02d}]]"
            after_text = ""
            if clean_blocks:
                prev_block = clean_blocks[-1].strip()
                lines = [l for l in prev_block.split('\n') if l.strip()]
                after_text = lines[-1][:80] if lines else ""
            dividers.append({
                "block_index": block_index,
                "after_text": after_text,
                "placeholder": placeholder,
                "source_order": i,
            })
            clean_blocks.append(placeholder)
            continue

        code_match = code_pattern.match(block)
        if code_match:
            language = code_match.group(1).strip()
            code = code_match.group(2).rstrip('\n')

            block_index = len(clean_blocks)
            placeholder = f"[[CODE_BLOCK_{len(code_blocks) + 1:02d}]]"

            after_text = ""
            if clean_blocks:
                prev_block = clean_blocks[-1].strip()
                lines = [l for l in prev_block.split('\n') if l.strip()]
                after_text = lines[-1][:80] if lines else ""

            code_blocks.append({
                "language": language,
                "code": code,
                "block_index": block_index,
                "after_text": after_text,
                "placeholder": placeholder,
                "source_order": i,
            })
            clean_blocks.append(placeholder)
            continue

        image = parse_image_block(block_stripped)
        if image:
            alt_text = image["label"]
            img_path = image["destination"]
            full_path, exists = resolve_image_path(img_path, base_path, asset_roots)

            block_index = len(clean_blocks)

            after_text = ""
            if clean_blocks:
                prev_block = clean_blocks[-1].strip()
                lines = [l for l in prev_block.split('\n') if l.strip()]
                after_text = lines[-1][:80] if lines else ""

            images.append({
                "path": full_path,
                "original_path": img_path,
                "exists": exists,
                "alt": alt_text,
                "block_index": block_index,
                "after_text": after_text,
                "source_order": i,
            })
            if len(images) > 1:
                placeholder = f"[[IMAGE_{len(images) - 1:02d}]]"
                images[-1]["placeholder"] = placeholder
                clean_blocks.append(placeholder)
        else:
            clean_blocks.append(block)

    clean_markdown = '\n\n'.join(clean_blocks)
    return images, dividers, code_blocks, clean_markdown, len(clean_blocks)


def extract_title(markdown: str) -> tuple[str, str]:
    """Extract title from first H1, H2, or first non-empty line.

    Returns:
        (title, markdown_without_title): Title string and markdown with H1 title removed.
        If title is from H1, it's removed from markdown to avoid duplication.
    """
    lines = markdown.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    title = "Untitled"
    title_line_idx = None

    active_fence = None
    visible_lines = []
    for idx, line in enumerate(lines):
        marker = fence_marker(line)
        if active_fence is not None:
            if (
                marker is not None
                and marker[0] == active_fence[0]
                and marker[1] >= active_fence[1]
                and not marker[2].strip()
            ):
                active_fence = None
            continue
        if marker is not None:
            active_fence = marker
            continue
        if line.startswith(("    ", "\t")):
            continue
        visible_lines.append((idx, line))

    for idx, line in visible_lines:
        match = re.match(r'^ {0,3}# (.+)$', line)
        if match:
            title = match.group(1).strip()
            title_line_idx = idx
            break

    if title_line_idx is None:
        for idx, line in visible_lines:
            match = re.match(r'^ {0,3}## (.+)$', line)
            if match:
                title = match.group(1).strip()
                title_line_idx = idx
                break
        else:
            for _, line in visible_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('!['):
                    title = stripped[:100]
                    break

    # Remove H1 title line from markdown to avoid duplication
    if title_line_idx is not None:
        lines.pop(title_line_idx)
        markdown = '\n'.join(lines)

    return title, markdown


def extract_blog_url(frontmatter: str) -> str | None:
    """Extract publish.blog.url from simple YAML frontmatter without a YAML dependency."""
    in_publish = False
    in_blog = False

    for line in frontmatter.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(' '))

        if not stripped or stripped.startswith('#'):
            continue

        if indent == 0:
            in_publish = stripped == 'publish:'
            in_blog = False
            continue

        if in_publish and indent == 2:
            in_blog = stripped == 'blog:'
            continue

        if in_publish and in_blog and indent == 4 and stripped.startswith('url:'):
            value = stripped.removeprefix('url:').strip().strip('"').strip("'")
            if value and not is_safe_http_url(value):
                raise ValueError("publish.blog.url must use an absolute http or https URL")
            return value or None

    return None


def is_safe_http_url(value: str) -> bool:
    """Return whether a URL is an absolute HTTP(S) URL."""
    if any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        return False
    parsed = urllib.parse.urlsplit(value)
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def render_markdown_links(markdown: str) -> str:
    """Render balanced Markdown links while escaping unsafe destinations."""
    rendered = []
    cursor = 0

    while cursor < len(markdown):
        start = markdown.find("[", cursor)
        if start == -1:
            rendered.append(markdown[cursor:])
            break
        prefix = markdown[cursor:start]
        preceding_escapes = len(prefix) - len(prefix.rstrip("\\"))
        if preceding_escapes % 2 == 1:
            rendered.append(prefix[:-1])
            rendered.append("[")
            cursor = start + 1
            continue
        rendered.append(prefix)
        if start > 0 and markdown[start - 1] == "!":
            rendered.append("[")
            cursor = start + 1
            continue

        parsed = parse_markdown_link_at(markdown, start)
        if parsed is None:
            rendered.append("[")
            cursor = start + 1
            continue

        label = parsed["label"]
        url = html.unescape(parsed["destination"]).strip()
        if is_safe_http_url(url):
            rendered.append(
                f'<a href="{html.escape(url, quote=True)}">{label}</a>'
            )
        else:
            rendered.append(label)
        cursor = parsed["end"]

    return ''.join(rendered)


def split_frontmatter(content: str) -> tuple[str, str]:
    """Split YAML frontmatter only on standalone delimiter lines."""
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return "", content

    for index, line in enumerate(lines[1:], 1):
        if line == "---":
            return '\n'.join(lines[1:index]), '\n'.join(lines[index + 1:]).strip()

    return "", content


def render_markdown_lists(markdown: str) -> str:
    """Render flat Markdown lists with markers, starts, and continuations."""
    rendered_lines: list[str] = []
    active_list = None
    current_item: list[str] = []

    def flush_item() -> None:
        if current_item:
            rendered_lines.append(f"<li>{' '.join(current_item)}</li>")
            current_item.clear()

    def close_list() -> None:
        nonlocal active_list
        flush_item()
        if active_list is not None:
            rendered_lines.append(f"</{active_list}>")
            active_list = None

    for line in markdown.splitlines():
        unordered = re.match(r'^[-+*]\s+(.+)$', line)
        ordered = re.match(r'^(\d+)[.)]\s+(.+)$', line)
        list_kind = "ul" if unordered else "ol" if ordered else None

        if list_kind is not None:
            if list_kind != active_list:
                close_list()
                if ordered:
                    start = int(ordered.group(1))
                    start_attr = f' start="{start}"' if start != 1 else ""
                    rendered_lines.append(f"<ol{start_attr}>")
                else:
                    rendered_lines.append("<ul>")
            else:
                flush_item()
            active_list = list_kind
            current_item.append(
                unordered.group(1) if unordered else ordered.group(2)
            )
        elif active_list is not None and line.strip():
            if line.startswith(("<h2>", "<h3>", "<blockquote>", "[[")):
                close_list()
                rendered_lines.append(line)
            else:
                current_item.append(line.strip())
        else:
            close_list()
            rendered_lines.append(line)

    close_list()

    return '\n'.join(rendered_lines)


def markdown_to_html(markdown: str) -> str:
    """Convert markdown to HTML for X Articles rich text paste."""
    rendered = html.escape(markdown, quote=False)

    # Headers (H2 only, H1 is title)
    rendered = re.sub(r'^## (.+)$', r'<h2>\1</h2>', rendered, flags=re.MULTILINE)
    rendered = re.sub(r'^### (.+)$', r'<h3>\1</h3>', rendered, flags=re.MULTILINE)

    # Bold
    rendered = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', rendered)

    # Italic
    rendered = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', rendered)

    # Links. Unsafe schemes retain their visible label without becoming anchors.
    rendered = render_markdown_links(rendered)

    # Blockquotes (regular markdown blockquotes, not code blocks)
    rendered = re.sub(
        r'^&gt; (.+)$',
        r'<blockquote>\1</blockquote>',
        rendered,
        flags=re.MULTILINE,
    )

    # Preserve ordered versus unordered list runs.
    rendered = render_markdown_lists(rendered)

    # Paragraphs - split by double newlines
    parts = rendered.split('\n\n')
    processed_parts = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Skip if already a block element
        if part.startswith(('<h2>', '<h3>', '<blockquote>', '<ul', '<ol')):
            processed_parts.append(part)
        else:
            # Treat single newlines inside a paragraph as Markdown soft wraps.
            part = re.sub(r'\s*\n\s*', ' ', part)
            processed_parts.append(f'<p>{part}</p>')

    return ''.join(processed_parts)


def parse_markdown_file(
    filepath: str,
    asset_root: str | None = None,
    additional_asset_roots: list[str] | None = None,
) -> dict:
    """Parse a markdown file and return structured data."""
    path = Path(filepath).expanduser().resolve()
    base_path = path.parent
    approved_asset_root = (
        Path(asset_root).expanduser().resolve() if asset_root else base_path
    )
    approved_asset_roots = (approved_asset_root,) + tuple(
        Path(root).expanduser().resolve()
        for root in (additional_asset_roots or [])
    )

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    frontmatter, content = split_frontmatter(content)
    if (
        RESERVED_PLACEHOLDER_PATTERN.search(content)
        or RESERVED_SENTINEL_PATTERN.search(content)
    ):
        raise ValueError(
            "article source contains a reserved native-insertion marker"
        )

    blog_url = extract_blog_url(frontmatter)

    # Extract title first (and remove H1 from markdown)
    title, content = extract_title(content)

    # Extract blocks that must be inserted through native X editor controls.
    images, dividers, code_blocks, clean_markdown, total_blocks = extract_insert_blocks(
        content,
        base_path,
        approved_asset_roots,
    )

    if blog_url:
        cross_post = f"This article is cross-posted on my blog: [{blog_url}]({blog_url})."
        if not clean_markdown.rstrip().endswith(cross_post):
            clean_markdown = (
                f"{clean_markdown}\n\n{cross_post}"
                if clean_markdown.strip()
                else cross_post
            )
            total_blocks += 1

    # Convert to HTML
    html = markdown_to_html(clean_markdown)

    cover_image = images[0]["path"] if images else None
    cover_exists = images[0]["exists"] if images else True
    content_images = images[1:] if len(images) > 1 else []
    insertions = sorted(
        [
            *({"kind": "image", **item} for item in content_images),
            *({"kind": "divider", **item} for item in dividers),
            *({"kind": "code", **item} for item in code_blocks),
        ],
        key=lambda item: item["source_order"],
    )

    missing = [img for img in images if not img["exists"]]
    if missing:
        print(f"[parse_markdown] WARNING: {len(missing)} image(s) not found", file=sys.stderr)

    return {
        "title": title,
        "cover_image": cover_image,
        "cover_exists": cover_exists,
        "content_images": content_images,
        "dividers": dividers,
        "code_blocks": code_blocks,
        "insertions": insertions,
        "blog_url": blog_url,
        "html": html,
        "total_blocks": total_blocks,
        "source_file": str(path),
        "asset_root": str(approved_asset_root),
        "asset_roots": [str(root) for root in approved_asset_roots],
        "missing_images": len(missing)
    }


def main():
    parser = argparse.ArgumentParser(description='Parse Markdown for X Articles')
    parser.add_argument('file', help='Markdown file to parse')
    parser.add_argument('--output', choices=['json', 'html'], default='json',
                       help='Output format (default: json)')
    parser.add_argument('--html-only', action='store_true',
                       help='Output only HTML content')
    parser.add_argument(
        '--asset-root',
        help='Approved root for all local images (defaults to the Markdown directory)',
    )
    parser.add_argument(
        '--additional-asset-root',
        action='append',
        default=[],
        help='Additional narrow approved image root; may be repeated',
    )

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        result = parse_markdown_file(
            args.file,
            asset_root=args.asset_root,
            additional_asset_roots=args.additional_asset_root,
        )
    except (UnsafeAssetPath, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.html_only:
        print(result['html'])
    elif args.output == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result['html'])


if __name__ == '__main__':
    main()
