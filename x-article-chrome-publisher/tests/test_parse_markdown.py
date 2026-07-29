import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "parse_markdown.py"
SPEC = importlib.util.spec_from_file_location("parse_markdown", SCRIPT)
parse_markdown = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(parse_markdown)


class AssetPathTests(unittest.TestCase):
    def test_image_inside_default_asset_root_is_canonicalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "cover.png"
            image.write_bytes(b"png")
            article = root / "article.md"
            article.write_text("# Title\n\n![cover](./cover.png)\n", encoding="utf-8")

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertEqual(result["cover_image"], str(image.resolve()))
            self.assertTrue(result["cover_exists"])
            self.assertEqual(result["asset_root"], str(root.resolve()))

    def test_parent_escape_is_rejected_even_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article_dir = root / "article"
            article_dir.mkdir()
            outside = root / "outside.png"
            outside.write_bytes(b"png")
            article = article_dir / "article.md"
            article.write_text("# Title\n\n![cover](../outside.png)\n", encoding="utf-8")

            with self.assertRaises(parse_markdown.UnsafeAssetPath):
                parse_markdown.parse_markdown_file(str(article))

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article_dir = root / "article"
            article_dir.mkdir()
            outside = root / "outside.png"
            outside.write_bytes(b"png")
            (article_dir / "cover.png").symlink_to(outside)
            article = article_dir / "article.md"
            article.write_text("# Title\n\n![cover](cover.png)\n", encoding="utf-8")

            with self.assertRaises(parse_markdown.UnsafeAssetPath):
                parse_markdown.parse_markdown_file(str(article))

    def test_explicit_temporary_asset_root_does_not_widen_article_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article_dir = root / "article"
            generated_dir = root / "generated"
            outside_dir = root / "outside"
            article_dir.mkdir()
            generated_dir.mkdir()
            outside_dir.mkdir()
            generated = generated_dir / "table.png"
            generated.write_bytes(b"png")
            outside = outside_dir / "private.png"
            outside.write_bytes(b"png")
            article = article_dir / "article.md"
            article.write_text(
                f"# Title\n\n![table]({generated})\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(
                str(article),
                additional_asset_roots=[str(generated_dir)],
            )
            self.assertEqual(result["cover_image"], str(generated.resolve()))

            article.write_text(
                f"# Title\n\n![private]({outside})\n",
                encoding="utf-8",
            )
            with self.assertRaises(parse_markdown.UnsafeAssetPath):
                parse_markdown.parse_markdown_file(
                    str(article),
                    additional_asset_roots=[str(generated_dir)],
                )

    def test_parenthesized_image_filename_remains_a_native_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "cover_(1).png"
            image.write_bytes(b"png")
            article = root / "article.md"
            article.write_text(
                "# Title\n\n![cover](cover_(1).png)\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertEqual(result["cover_image"], str(image.resolve()))


class HtmlSafetyTests(unittest.TestCase):
    def test_raw_html_is_escaped_and_unsafe_links_are_not_anchors(self):
        rendered = parse_markdown.markdown_to_html(
            '<img src=x onerror="alert(1)">\n\n'
            "[unsafe](javascript:alert(1))\n\n"
            "[safe](https://example.com/?a=1&b=2)"
        )

        self.assertNotIn("<img", rendered)
        self.assertIn("&lt;img", rendered)
        self.assertNotIn("href=\"javascript:", rendered)
        self.assertIn(
            '<a href="https://example.com/?a=1&amp;b=2">safe</a>',
            rendered,
        )
        self.assertIn(
            '<a href="https://example.com/Foo_(bar)">wiki</a>',
            parse_markdown.markdown_to_html(
                "[wiki](https://example.com/Foo_(bar))"
            ),
        )

    def test_frontmatter_blog_url_requires_http_or_https(self):
        with self.assertRaises(ValueError):
            parse_markdown.extract_blog_url(
                "publish:\n  blog:\n    url: javascript:alert(1)"
            )
        with self.assertRaises(ValueError):
            parse_markdown.extract_blog_url(
                "publish:\n  blog:\n    url: https://example.com/a b"
            )
        self.assertTrue(parse_markdown.is_safe_http_url("https://example.com/a%20b"))

    def test_ordered_and_unordered_lists_keep_their_list_kind(self):
        ordered = parse_markdown.markdown_to_html("1. First\n2. Second")
        unordered = parse_markdown.markdown_to_html("- First\n- Second")
        mixed = parse_markdown.markdown_to_html("1. First\n- Second")
        ordinary = parse_markdown.markdown_to_html(
            "+ First\n  continuation\n* Second\n\n3. Third"
        )

        self.assertEqual(ordered, "<ol>\n<li>First</li>\n<li>Second</li>\n</ol>")
        self.assertEqual(unordered, "<ul>\n<li>First</li>\n<li>Second</li>\n</ul>")
        self.assertEqual(
            mixed,
            "<ol>\n<li>First</li>\n</ol>\n<ul>\n<li>Second</li>\n</ul>",
        )
        self.assertEqual(
            ordinary,
            "<ul>\n<li>First continuation</li>\n<li>Second</li>\n</ul>"
            '<ol start="3">\n<li>Third</li>\n</ol>',
        )

    def test_first_h1_wins_even_when_prose_precedes_it(self):
        title, body = parse_markdown.extract_title(
            "Intro text\n\n# Actual Title\n\nBody"
        )

        self.assertEqual(title, "Actual Title")
        self.assertNotIn("# Actual Title", body)
        self.assertIn("Intro text", body)

    def test_code_comments_do_not_become_titles(self):
        title, body = parse_markdown.extract_title(
            "```sh\n# install dependencies\nnpm install\n```\n\n# Real Title"
        )

        self.assertEqual(title, "Real Title")
        self.assertIn("# install dependencies", body)
        self.assertNotIn("# Real Title", body)

    def test_indented_code_comment_does_not_become_title(self):
        title, body = parse_markdown.extract_title(
            "    # code comment\n\n# Real Title\n\nBody"
        )

        self.assertEqual(title, "Real Title")
        self.assertIn("    # code comment", body)
        self.assertNotIn("# Real Title", body)

    def test_tilde_and_long_backtick_fences_preserve_code_and_real_title(self):
        markdown = (
            "~~~md\n# Not a title\n~~~\n\n"
            "````text\n``` is content\n# Also not a title\n````\n\n"
            "# Real Title"
        )
        title, body = parse_markdown.extract_title(markdown)
        blocks = parse_markdown.split_into_blocks(body)

        self.assertEqual(title, "Real Title")
        self.assertEqual(len(blocks), 2)
        self.assertIn("# Not a title", blocks[0])
        self.assertIn("``` is content", blocks[1])
        self.assertIn("# Also not a title", blocks[1])

    def test_h2_fallback_is_removed_from_body(self):
        title, body = parse_markdown.extract_title("## Subtitle\n\nBody")

        self.assertEqual(title, "Subtitle")
        self.assertNotIn("## Subtitle", body)
        self.assertEqual(body.strip(), "Body")

    def test_frontmatter_delimiters_must_be_standalone_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text(
                "---\n"
                "description: alpha---omega\n"
                "publish:\n"
                "  blog:\n"
                "    url: https://example.com/post\n"
                "---\n"
                "# Actual Title\n\nBody\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertEqual(result["title"], "Actual Title")
            self.assertEqual(result["blog_url"], "https://example.com/post")
            self.assertNotIn("description:", result["html"])

    def test_indented_yaml_separator_does_not_end_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text(
                "---\n"
                "description: |\n"
                "  ---\n"
                "  internal note\n"
                "publish:\n"
                "  blog:\n"
                "    url: https://example.com/post\n"
                "---\n"
                "# Actual Title\n\nBody\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertEqual(result["title"], "Actual Title")
            self.assertEqual(result["blog_url"], "https://example.com/post")
            self.assertNotIn("internal note", result["html"])

    def test_existing_blog_link_does_not_suppress_terminal_cross_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text(
                "---\n"
                "publish:\n"
                "  blog:\n"
                "    url: https://example.com/post\n"
                "---\n"
                "# Title\n\n"
                "Earlier mention: [post](https://example.com/post).\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertIn(
                "This article is cross-posted on my blog:",
                result["html"],
            )
            self.assertGreaterEqual(
                result["html"].count("https://example.com/post"),
                2,
            )

    def test_lazy_list_continuation_stays_in_the_current_item(self):
        rendered = parse_markdown.markdown_to_html(
            "- first\nlazy continuation\n- second"
        )

        self.assertEqual(
            rendered,
            "<ul>\n<li>first lazy continuation</li>\n<li>second</li>\n</ul>",
        )

    def test_escaped_label_and_quoted_parenthesis_title_parse_cleanly(self):
        rendered = parse_markdown.markdown_to_html(
            r'[label \] more](https://example.com "title ) text")'
        )

        self.assertEqual(
            rendered,
            '<p><a href="https://example.com">label ] more</a></p>',
        )

    def test_destination_quotes_escapes_and_escaped_opening_bracket(self):
        rendered = parse_markdown.markdown_to_html(
            "[apostrophe](https://example.com/it's)\n\n"
            r"[escaped](https://example.com/a\)b)" "\n\n"
            r"\[literal](https://example.com)"
        )

        self.assertIn(
            '<a href="https://example.com/it&#x27;s">apostrophe</a>',
            rendered,
        )
        self.assertIn(
            '<a href="https://example.com/a)b">escaped</a>',
            rendered,
        )
        self.assertIn("[literal](https://example.com)", rendered)
        self.assertNotIn('href="https://example.com">literal</a>', rendered)

    def test_escaped_parenthesis_image_path_is_unescaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "cover_(1).png"
            image.write_bytes(b"png")
            article = root / "article.md"
            article.write_text(
                r"# Title" "\n\n" r"![cover](cover_\(1\).png)" "\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertEqual(result["cover_image"], str(image.resolve()))

    def test_parenthesized_image_with_quoted_title_is_canonicalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "cover_(1).png"
            image.write_bytes(b"png")
            article = root / "article.md"
            article.write_text(
                '# Title\n\n![cover \\] image](cover_(1).png "title ) text")\n',
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertEqual(result["cover_image"], str(image.resolve()))
            self.assertEqual(result["title"], "Title")

    def test_native_insertions_keep_placeholders_and_source_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cover = root / "cover.png"
            body_image = root / "body.png"
            cover.write_bytes(b"png")
            body_image.write_bytes(b"png")
            article = root / "article.md"
            article.write_text(
                "# Title\n\n"
                "Intro\n\n"
                "![cover](cover.png)\n\n"
                "```python\nprint('hello')\n```\n\n"
                "![body](body.png)\n\n"
                "---\n\n"
                "End\n",
                encoding="utf-8",
            )

            result = parse_markdown.parse_markdown_file(str(article))

            self.assertIn("[[CODE_BLOCK_01]]", result["html"])
            self.assertIn("[[IMAGE_01]]", result["html"])
            self.assertIn("[[DIVIDER_01]]", result["html"])
            self.assertLess(
                result["html"].index("[[CODE_BLOCK_01]]"),
                result["html"].index("[[IMAGE_01]]"),
            )
            self.assertLess(
                result["html"].index("[[IMAGE_01]]"),
                result["html"].index("[[DIVIDER_01]]"),
            )
            self.assertEqual(
                [item["kind"] for item in result["insertions"]],
                ["code", "image", "divider"],
            )
            self.assertEqual(
                [item["placeholder"] for item in result["insertions"]],
                ["[[CODE_BLOCK_01]]", "[[IMAGE_01]]", "[[DIVIDER_01]]"],
            )

    def test_authored_native_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            for placeholder in (
                "[[CODE_BLOCK_01]]",
                "[[IMAGE_01]]",
                "[[DIVIDER_01]]",
                "___DIVIDER___",
                "___CODE_BLOCK_START___",
                "___CODE_BLOCK_CONTENT___",
                "___CODE_BLOCK_END___",
            ):
                article.write_text(
                    f"# Title\n\nLiteral {placeholder}\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "reserved"):
                    parse_markdown.parse_markdown_file(str(article))


if __name__ == "__main__":
    unittest.main()
