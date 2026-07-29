import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "table_to_image.py"
SPEC = importlib.util.spec_from_file_location("table_to_image", SCRIPT)
table_to_image = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(table_to_image)


class MarkdownTableTests(unittest.TestCase):
    def test_escaped_pipes_and_code_span_pipes_stay_in_cells(self):
        headers, rows, alignments = table_to_image.parse_markdown_table(
            "| Header | Value |\n"
            "| --- | --- |\n"
            "| one \\| two | `left | right` |\n"
        )

        self.assertEqual(headers, ["Header", "Value"])
        self.assertEqual(rows, [["one | two", "`left | right`"]])
        self.assertEqual(alignments, ["left", "left"])

    def test_mismatched_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "same column count"):
            table_to_image.parse_markdown_table(
                "| Header | Value |\n"
                "| --- | --- |\n"
                "| one | two | extra |\n"
            )


if __name__ == "__main__":
    unittest.main()
