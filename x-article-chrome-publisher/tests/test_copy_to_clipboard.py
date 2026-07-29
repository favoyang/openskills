import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "copy_to_clipboard.py"
SPEC = importlib.util.spec_from_file_location("copy_to_clipboard", SCRIPT)
copy_to_clipboard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(copy_to_clipboard)


class PlainTextFallbackTests(unittest.TestCase):
    def test_html_fallback_is_readable_and_contains_no_markup(self):
        plain = copy_to_clipboard.html_to_plain_text(
            "<h2>Heading</h2><p>Hello <strong>world</strong>.</p>"
            "<ul><li>First</li><li>Second &amp; safe</li></ul>"
        )

        self.assertEqual(
            plain,
            "Heading\nHello world.\n- First\n- Second & safe",
        )
        self.assertNotIn("<", plain)

    def test_compressed_png_uses_converted_tiff_pasteboard_data(self):
        self.assertEqual(
            copy_to_clipboard.macos_image_pasteboard_format("image.png", 85),
            "tiff",
        )
        self.assertEqual(
            copy_to_clipboard.macos_image_pasteboard_format("image.png", None),
            "png",
        )

    def test_jpeg_normalization_handles_advertised_png_modes(self):
        class FakeImage:
            def __init__(self, mode, info=None):
                self.mode = mode
                self.info = info or {}
                self.size = (10, 10)
                self.pasted = False

            def convert(self, mode):
                return FakeImage(mode)

            def getchannel(self, channel):
                self.channel = channel
                return object()

            def paste(self, source, mask):
                self.pasted = True

        class FakeImageModule:
            @staticmethod
            def new(mode, size, color):
                return FakeImage(mode)

        for mode, info in (
            ("RGB", {}),
            ("RGBA", {}),
            ("P", {}),
            ("P", {"transparency": 0}),
            ("LA", {}),
        ):
            with self.subTest(mode=mode, info=info):
                normalized = copy_to_clipboard.normalize_image_for_jpeg(
                    FakeImage(mode, info),
                    FakeImageModule,
                )
                self.assertIn(normalized.mode, {"RGB", "L", "CMYK"})
                if mode in {"RGBA", "LA"} or "transparency" in info:
                    self.assertTrue(normalized.pasted)

    def test_windows_dib_encoder_converts_cmyk_to_rgb(self):
        class FakeImage:
            def __init__(self, mode):
                self.mode = mode

            def convert(self, mode):
                return FakeImage(mode)

            def save(self, output, format):
                if self.mode != "RGB" or format != "BMP":
                    raise ValueError("unsupported encoder mode")
                output.write(b"x" * 14 + b"dib-data")

        self.assertEqual(
            copy_to_clipboard.encode_windows_dib(FakeImage("CMYK")),
            b"dib-data",
        )


if __name__ == "__main__":
    unittest.main()
