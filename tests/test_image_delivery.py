"""Exercise the image policy through real clean and incremental Sphinx builds."""

from html.parser import HTMLParser
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


EXTENSIONS = Path(__file__).resolve().parents[1] / "docs" / "_ext"


class Images(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            attrs = dict(attrs)
            self.images[attrs.get("alt")] = attrs


def png(width=400, height=200):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\xff\xff" * width) * height))
            + chunk(b"IEND", b""))


class ImageDeliveryTests(unittest.TestCase):
    def test_generated_html_preserves_authored_intent_and_incremental_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source", root / "html"
            (source / "nested").mkdir(parents=True)
            (source / "assets").mkdir()
            (source / "assets" / "sample.png").write_bytes(png())
            (source / "assets" / "vector.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"/>')
            (source / "conf.py").write_text(
                f"import sys\nsys.path.insert(0, {str(EXTENSIONS)!r})\n"
                "extensions = ['image_delivery']\n"
                "html_theme = 'sphinx_rtd_theme'\n")
            (source / "index.rst").write_text(
                "Images\n======\n\n.. toctree::\n\n   nested/page\n")
            page = source / "nested" / "page.rst"
            page.write_text(
                "Policy\n======\n\n"
                ".. image:: https://example.invalid/external.png\n"
                "   :alt: external decoding=hint\n\n"
                ".. image:: ../assets/sample.png\n   :alt: first\n\n"
                ".. image:: ../assets/sample.png\n   :alt: second\n"
                "   :target: ../assets/sample.png\n\n"
                ".. image:: ../assets/sample.png\n   :alt: width\n   :width: 120px\n\n"
                ".. image:: ../assets/sample.png\n   :alt: height\n   :height: 60px\n\n"
                ".. image:: ../assets/sample.png\n   :alt: percent\n   :width: 50%\n\n"
                ".. image:: ../assets/sample.png\n   :alt: both\n"
                "   :width: 100px\n   :height: 70px\n\n"
                ".. image:: ../assets/sample.png\n   :alt: scaled\n   :scale: 50%\n\n"
                ".. image:: ../assets/sample.png\n   :alt: explicit\n   :loading: link\n\n"
                ".. image:: ../assets/vector.svg\n   :alt: vector\n\n"
                ".. image:: data:image/png;base64,iVBORw0KGgo=\n   :alt: data\n")

            def build(builder="html", *options):
                result = subprocess.run(
                    [sys.executable, "-m", "sphinx", "-b", builder, "-W", "-q",
                     *options, str(source), str(output if builder == "html" else root / builder)],
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            for options in (("-E", "-a"), ()):
                # Touch the source to force a write using the cached environment.
                page.write_text(page.read_text() + "\n")
                build("html", *options)
                html = (output / "nested" / "page.html").read_text()
                images = Images(html).images
                with self.subTest(build=options):
                    self.assertEqual(images["first"]["loading"], "eager")
                    self.assertEqual(images["second"]["loading"], "lazy")
                    self.assertEqual(images["first"]["width"], "400")
                    self.assertEqual(images["first"]["height"], "200")
                    self.assertEqual(images["scaled"]["width"], "200")
                    self.assertEqual(images["scaled"]["height"], "100")
                    for name, style in (("width", "width: 120px;"),
                                        ("height", "height: 60px;"),
                                        ("percent", "width: 50%;"),
                                        ("both", "width: 100px; height: 70px;")):
                        self.assertEqual(images[name].get("style"), style)
                    self.assertNotIn("loading", images["explicit"])
                    self.assertIn('href="../assets/sample.png"', html)
                    for image in images.values():
                        self.assertEqual(image["decoding"], "async")
                    for name in ("external decoding=hint", "data"):
                        self.assertNotIn("width", images[name])
                        self.assertNotIn("loading", images[name])
                    self.assertEqual(images["vector"]["width"], "40")
                    self.assertEqual(images["vector"]["height"], "20")

            # Reordering must recompute first-image status on incremental writes.
            page.write_text("Policy\n======\n\n"
                            ".. image:: ../assets/sample.png\n   :alt: explicit-first\n"
                            "   :loading: lazy\n\n"
                            ".. image:: ../assets/sample.png\n   :alt: second\n")
            build()
            images = Images((output / "nested" / "page.html").read_text()).images
            self.assertEqual(images["explicit-first"]["loading"], "lazy")
            self.assertEqual(images["second"]["loading"], "lazy")

            page.write_text("Policy\n======\n\n"
                            ".. image:: ../assets/sample.png\n   :alt: second\n\n"
                            ".. image:: ../assets/sample.png\n   :alt: first\n")
            build()
            images = Images((output / "nested" / "page.html").read_text()).images
            self.assertEqual(images["second"]["loading"], "eager")
            self.assertEqual(images["first"]["loading"], "lazy")
            build("latex", "-E", "-a")
            tex = next((root / "latex").glob("*.tex")).read_text()
            self.assertNotIn(r"400\sphinxpxdimen", tex)
            self.assertNotIn(r"200\sphinxpxdimen", tex)


if __name__ == "__main__":
    unittest.main()
