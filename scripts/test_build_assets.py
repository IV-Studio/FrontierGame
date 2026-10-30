import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from build_assets import Publisher


class PublisherTest(unittest.TestCase):
    def test_archives_and_replaces_every_existing_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "docs" / "assets"
            directory = assets / "boards"
            directory.mkdir(parents=True)
            old_url = directory / "board-main-1111111111.png"
            current_url = directory / "board-main-2222222222.png"
            old_url.write_bytes(b"older artwork")
            current_url.write_bytes(b"current artwork")
            catalog = root / "docs" / "catalog.json"
            catalog.write_text(json.dumps({"boards": [{"path":
                "assets/boards/board-main-2222222222.png"}]}), encoding="utf-8")

            archive = root / "archive" / "assets"
            publisher = Publisher(assets, archive, catalog)
            result = publisher(Image.new("RGB", (2, 2), "red"),
                               "boards", "board-main")

            self.assertEqual(result["path"],
                             "assets/boards/board-main-2222222222.png")
            self.assertEqual(old_url.read_bytes(), current_url.read_bytes())
            archived = list((archive / "boards" / "board-main").glob("*.png"))
            self.assertEqual({path.read_bytes() for path in archived},
                             {b"older artwork", b"current artwork"})

            publisher(Image.new("RGB", (2, 2), "red"),
                      "boards", "board-main")
            self.assertEqual(len(list((archive / "boards" / "board-main").glob("*.png"))), 2)

    def test_retires_only_unlisted_assets_and_archives_their_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "docs" / "assets"
            directory = assets / "boards"
            directory.mkdir(parents=True)
            retired = directory / "board-edge-1111111111.png"
            retired.write_bytes(b"retired artwork")
            active = directory / "board-main-2222222222.png"
            active.write_bytes(b"old main board")
            archive = root / "archive" / "assets"
            publisher = Publisher(assets, archive, root / "docs" / "catalog.json")
            publisher(Image.new("RGB", (2, 2), "red"), "boards", "board-main")

            self.assertEqual(publisher.retire_unlisted(), ["boards/board-edge-1111111111.png"])
            self.assertFalse(retired.exists())
            self.assertTrue(active.exists())
            saved = list((archive / "boards" / "board-edge").glob("*.png"))
            self.assertEqual([path.read_bytes() for path in saved], [b"retired artwork"])


if __name__ == "__main__":
    unittest.main()
