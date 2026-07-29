#!/usr/bin/env python3
from __future__ import annotations

"""
Convert Markdown table to PNG image.

For X Articles publishing when native table rendering is not supported
(X Premium tier) or when you want consistent visual styling.

Usage:
    python3 table_to_image.py <input.md> <output.png> [--scale 2]

Arguments:
    input.md    - Markdown file containing a table
    output.png  - Output PNG file path
    --scale N   - Scale factor for high-DPI displays (default: 2)

Requirements:
    uv run --with pillow -- python3 table_to_image.py <input.md> <output.png>
"""

import sys
import re
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None


def parse_markdown_table(content: str) -> tuple[list[str], list[list[str]], list[str]]:
    """Parse markdown table into headers, rows, and alignments."""
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]

    if len(lines) < 2:
        raise ValueError("Table must have at least 2 rows")

    def parse_cells(line: str) -> list[str]:
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            before_pipe = line[:-1]
            trailing_backslashes = len(before_pipe) - len(before_pipe.rstrip('\\'))
            if trailing_backslashes % 2 == 0:
                line = before_pipe

        cells = []
        cell = []
        code_ticks = None
        i = 0
        while i < len(line):
            char = line[i]
            if char == '\\' and i + 1 < len(line) and line[i + 1] == '|':
                cell.append('|')
                i += 2
                continue
            if char == '`':
                run_end = i + 1
                while run_end < len(line) and line[run_end] == '`':
                    run_end += 1
                run_length = run_end - i
                if code_ticks is None:
                    code_ticks = run_length
                elif code_ticks == run_length:
                    code_ticks = None
                cell.append(line[i:run_end])
                i = run_end
                continue
            if char == '|' and code_ticks is None:
                cells.append(''.join(cell).strip())
                cell = []
            else:
                cell.append(char)
            i += 1

        cells.append(''.join(cell).strip())
        return cells

    # Find separator line
    separator_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^\|?[\s]*:?-{2,}:?[\s]*(\|[\s]*:?-{2,}:?[\s]*)*\|?$', line):
            separator_idx = i
            break

    if separator_idx > 0:
        # Has headers
        headers = parse_cells(lines[separator_idx - 1])
        sep_cells = parse_cells(lines[separator_idx])
        alignments = []
        for cell in sep_cells:
            cell = cell.strip()
            if cell.startswith(':') and cell.endswith(':'):
                alignments.append('center')
            elif cell.endswith(':'):
                alignments.append('right')
            else:
                alignments.append('left')
        rows = [parse_cells(line) for line in lines[separator_idx + 1:]]
        expected_columns = len(headers)
        if len(sep_cells) != expected_columns:
            raise ValueError("Table separator must match the header column count")
    else:
        # No headers - all data rows
        headers = []
        rows = [parse_cells(line) for line in lines]
        alignments = ['left'] * (len(rows[0]) if rows else 0)
        expected_columns = len(rows[0]) if rows else 0

    if any(len(row) != expected_columns for row in rows):
        raise ValueError("Every table row must have the same column count")

    return headers, rows, alignments


def get_font(size: int, bold: bool = False):
    """Get a font, falling back to default if system fonts unavailable."""
    font_paths = [
        # macOS
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        # macOS Chinese fonts
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue

    # Fallback to default
    return ImageFont.load_default()


def render_table_to_image(
    headers: list[str],
    rows: list[list[str]],
    alignments: list[str],
    scale: int = 2
) -> Image.Image:
    """Render table data to a PIL Image."""
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError(
            "Pillow not installed. Run through `uv run --with pillow -- python3 ...`."
        )

    expected_columns = len(headers) if headers else (len(rows[0]) if rows else 0)
    if any(len(row) != expected_columns for row in rows):
        raise ValueError("Every table row must have the same column count")

    # Configuration
    base_font_size = 14
    font_size = base_font_size * scale
    padding_x = 16 * scale
    padding_y = 12 * scale
    border_radius = 8 * scale
    margin = 20 * scale

    # Colors
    bg_color = (255, 255, 255)
    header_bg = (249, 250, 251)
    text_color = (55, 65, 81)
    header_text_color = (17, 24, 39)
    border_color = (229, 231, 235)

    # Fonts
    regular_font = get_font(font_size)
    bold_font = get_font(font_size, bold=True)

    # Calculate column widths
    col_count = len(headers) if headers else (len(rows[0]) if rows else 0)
    col_widths = [0] * col_count

    # Create temp image for text measurement
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    # Measure headers
    for i, header in enumerate(headers):
        bbox = temp_draw.textbbox((0, 0), header, font=bold_font)
        col_widths[i] = max(col_widths[i], bbox[2] - bbox[0])

    # Measure data cells
    for row in rows:
        for i, cell in enumerate(row):
            if i < col_count:
                bbox = temp_draw.textbbox((0, 0), cell, font=regular_font)
                col_widths[i] = max(col_widths[i], bbox[2] - bbox[0])

    # Add padding to widths
    col_widths = [w + padding_x * 2 for w in col_widths]

    # Calculate dimensions
    row_height = font_size + padding_y * 2
    header_height = row_height if headers else 0
    table_width = sum(col_widths)
    table_height = header_height + len(rows) * row_height

    img_width = table_width + margin * 2
    img_height = table_height + margin * 2

    # Create image
    img = Image.new('RGB', (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw table border (rounded rectangle)
    x0, y0 = margin, margin
    x1, y1 = margin + table_width, margin + table_height
    draw.rounded_rectangle([x0, y0, x1, y1], radius=border_radius, outline=border_color, width=scale)

    y = margin

    # Draw header
    if headers:
        # Header background
        draw.rounded_rectangle(
            [x0, y0, x1, y0 + row_height],
            radius=border_radius,
            fill=header_bg
        )
        # Cover bottom corners of header (they should be square)
        draw.rectangle([x0, y0 + row_height - border_radius, x1, y0 + row_height], fill=header_bg)

        # Header border
        draw.line([(x0, y + row_height), (x1, y + row_height)], fill=border_color, width=scale)

        # Header text
        x = margin
        for i, header in enumerate(headers):
            bbox = draw.textbbox((0, 0), header, font=bold_font)
            text_width = bbox[2] - bbox[0]

            if alignments[i] == 'center':
                text_x = x + (col_widths[i] - text_width) // 2
            elif alignments[i] == 'right':
                text_x = x + col_widths[i] - text_width - padding_x
            else:
                text_x = x + padding_x

            text_y = y + padding_y
            draw.text((text_x, text_y), header, fill=header_text_color, font=bold_font)
            x += col_widths[i]

        y += row_height

    # Draw data rows
    for row_idx, row in enumerate(rows):
        # Row border (except last row)
        if row_idx < len(rows) - 1:
            draw.line([(x0, y + row_height), (x1, y + row_height)], fill=border_color, width=scale)

        # Cell text
        x = margin
        for i, cell in enumerate(row):
            bbox = draw.textbbox((0, 0), cell, font=regular_font)
            text_width = bbox[2] - bbox[0]

            if i < len(alignments):
                if alignments[i] == 'center':
                    text_x = x + (col_widths[i] - text_width) // 2
                elif alignments[i] == 'right':
                    text_x = x + col_widths[i] - text_width - padding_x
                else:
                    text_x = x + padding_x
            else:
                text_x = x + padding_x

            text_y = y + padding_y
            draw.text((text_x, text_y), cell, fill=text_color, font=regular_font)
            x += col_widths[i]

        y += row_height

    return img


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 table_to_image.py <input.md> <output.png> [--scale N]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Parse optional scale argument
    scale = 2
    if '--scale' in sys.argv:
        scale_idx = sys.argv.index('--scale')
        if scale_idx + 1 < len(sys.argv):
            try:
                scale = int(sys.argv[scale_idx + 1])
            except ValueError:
                pass

    # Read input
    content = Path(input_path).read_text()

    # Parse table
    try:
        headers, rows, alignments = parse_markdown_table(content)
    except Exception as e:
        print(f"Error parsing table: {e}")
        sys.exit(1)

    if not rows:
        print("Error: No data rows found in table")
        sys.exit(1)

    # Render image
    try:
        img = render_table_to_image(headers, rows, alignments, scale)
    except (RuntimeError, ValueError) as error:
        print(f"Error rendering table: {error}")
        sys.exit(1)

    # Save
    output = Path(output_path)
    img.save(output, 'PNG')
    print(f"Saved: {output} ({img.width}x{img.height})")


if __name__ == '__main__':
    main()
