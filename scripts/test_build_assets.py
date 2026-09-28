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


if __name__ == "__main__":
    unittest.main()
