"""Pack Figma exports while keeping Tabletop Simulator image URLs stable.

Input screenshots go in tmp/figma-export/. Existing published images are
archived before their bytes are replaced, including every older URL alias.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from pathlib import PurePosixPath

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp" / "figma-export"
ASSETS = ROOT / "docs" / "assets"
DOCS = ROOT / "docs"
ARCHIVE = ROOT / "archive" / "assets"


class Publisher:
    """Keep the catalog URL and all previously issued URLs current."""

    def __init__(self, assets: Path = ASSETS, archive: Path = ARCHIVE,
                 catalog_path: Path = DOCS / "catalog.json") -> None:
        self.assets = assets
        self.archive = archive
        self.preferred: dict[tuple[str, str], str] = {}
        if catalog_path.exists():
            self._read_paths(json.loads(catalog_path.read_text(encoding="utf-8")))

    def _read_paths(self, value: object) -> None:
        if isinstance(value, dict):
            path = value.get("path")
            if isinstance(path, str):
                parts = PurePosixPath(path).parts
                if len(parts) == 3 and parts[0] == "assets":
                    match = re.fullmatch(r"(.+?)(?:-[0-9a-f]{10})?\.png", parts[2])
                    if match:
                        self.preferred[(parts[1], match.group(1))] = parts[2]
            for child in value.values():
                self._read_paths(child)
        elif isinstance(value, list):
            for child in value:
                self._read_paths(child)

    def __call__(self, image: Image.Image, category: str, slug: str) -> dict:
        from io import BytesIO

        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        buffer = BytesIO()
        image.save(buffer, "PNG", optimize=True)
        data = buffer.getvalue()
        directory = self.assets / category
        directory.mkdir(parents=True, exist_ok=True)

        filename = self.preferred.get((category, slug), f"{slug}.png")
        alias_pattern = re.compile(rf"{re.escape(slug)}(?:-[0-9a-f]{{10}})?\.png")
        aliases = {path for path in directory.iterdir()
                   if path.is_file() and alias_pattern.fullmatch(path.name)}
        aliases.add(directory / filename)

        for path in sorted(aliases):
            if path.exists():
                old = path.read_bytes()
                if old == data:
                    continue
                digest = hashlib.sha256(old).hexdigest()[:12]
                saved = self.archive / category / slug / f"{digest}.png"
                saved.parent.mkdir(parents=True, exist_ok=True)
                if saved.exists() and saved.read_bytes() != old:
                    raise ValueError(f"Archive hash collision: {saved}")
                if not saved.exists():
                    saved.write_bytes(old)
            with tempfile.NamedTemporaryFile(dir=directory, prefix=f".{slug}.",
                                             suffix=".tmp", delete=False) as temp:
                temp.write(data)
                temp_path = Path(temp.name)
            try:
                os.replace(temp_path, path)
            finally:
                temp_path.unlink(missing_ok=True)

        return {"path": f"assets/{category}/{filename}",
                "width": image.width, "height": image.height}


def load(name: str) -> Image.Image:
    path = SOURCE / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing Figma export: {path}")
    return Image.open(path)


def sheet(name: str, count: int, source_columns: int, origin: tuple[int, int],
          stride: tuple[int, int], card_size: tuple[int, int],
          columns: int, rows: int) -> dict:
    image = load(name)
    mode = "RGBA" if "A" in image.getbands() else "RGB"
    result = Image.new(mode, (columns * card_size[0], rows * card_size[1]))
    for index in range(count):
        source_col = index % source_columns
        source_row = index // source_columns
        x = origin[0] + source_col * stride[0]
        y = origin[1] + source_row * stride[1]
        box = (x, y, x + card_size[0], y + card_size[1])
        if box[2] > image.width or box[3] > image.height:
            raise ValueError(f"Card {index + 1} falls outside {name} export")
        card = image.crop(box)
        result.paste(card, ((index % columns) * card_size[0],
                            (index // columns) * card_size[1]))
    return {"image": result, "count": count, "columns": columns,
            "rows": rows, "cardWidth": card_size[0], "cardHeight": card_size[1]}


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    publish = Publisher()
    catalog = {"source": "Figma Game components slice 218:13798", "boards": [],
               "cards": [], "references": [], "decks": [], "tokens": []}

    for slug, title, figma_id in [
        ("board-main", "Main board", "206:12165"),
        ("board-edge", "The Edge", "207:12552"),
        ("board-space-ports", "Space Ports", "207:12484"),
    ]:
        catalog["boards"].append({"title": title, "figmaId": figma_id,
                                   **publish(load(slug), "boards", slug)})

    for slug, title, figma_id in [
        ("card-action-guide", "Action Guide", "193:5684"),
        ("card-region-bonus-guide", "Region Bonus Guide", "193:5730"),
    ]:
        catalog["cards"].append({"title": title, "figmaId": figma_id,
                                  **publish(load(slug), "cards", slug)})

    catalog["references"].append({
        "title": "Board locations · regions and circle icons",
        "figmaId": "242:3938",
        **publish(load("board-locations"), "references", "board-locations"),
    })

    deck_specs = [
        ("monuments", "Monuments", "216:4802", 32, 6, (0, 0), (482, 680),
         (442, 640), 8, 4, "back-monument"),
        ("objectives", "Objectives", "193:5755", 30, 6, (196, 140), (420, 551),
         (388, 519), 6, 5, "back-objective"),
        ("specials", "Specials", "220:3842", 16, 5, (0, 0), (482, 680),
         (442, 640), 4, 4, "back-special"),
    ]
    for (slug, title, figma_id, count, source_columns, origin, stride,
         card_size, columns, rows, back_slug) in deck_specs:
        packed = sheet(slug, count, source_columns, origin, stride,
                       card_size, columns, rows)
        face = publish(packed.pop("image"), "decks", f"{slug}-faces")
        back = load(back_slug)
        if back.size != card_size:
            # TTS applies the same card geometry to both sides.
            back = back.resize(card_size, Image.Resampling.LANCZOS)
        back_asset = publish(back, "decks", f"{slug}-back")
        catalog["decks"].append({"title": title, "figmaId": figma_id,
                                  **packed, "face": face, "back": back_asset})

    for number in range(1, 7):
        for slug_prefix, title_prefix, ids in [
            ("action-tile", "Action tile", ["193:5655", "193:5672", "193:5675", "193:5678", "193:5660", "193:5669"]),
            ("spaceport", "Spaceport", ["193:6028", "193:6033", "193:6038", "193:6048", "193:6043", "193:6053"]),
        ]:
            slug = f"{slug_prefix}-{number}"
            catalog["tokens"].append({"title": f"{title_prefix} {number}",
                                      "figmaId": ids[number - 1],
                                      **publish(load(slug), "tokens", slug)})
    catalog["tokens"].append({"title": "Action tile 7", "figmaId": "229:13799",
                              **publish(load("action-tile-7"), "tokens", "action-tile-7")})

    manifest = json.dumps(catalog, indent=2, ensure_ascii=False)
    (DOCS / "catalog.json").write_text(manifest + "\n", encoding="utf-8")
    (DOCS / "catalog.js").write_text("window.FRONTIER_CATALOG = " +
                                      json.dumps(catalog, ensure_ascii=False) + ";\n",
                                      encoding="utf-8")
    index = DOCS / "index.html"
    version = hashlib.sha256(manifest.encode("utf-8")).hexdigest()[:10]
    html = index.read_text(encoding="utf-8")
    html = re.sub(r'catalog\.js\?v=[^" ]+', f'catalog.js?v={version}', html)
    index.write_text(html, encoding="utf-8")
    print(f"Built {len(catalog['decks'])} decks, {len(catalog['boards'])} boards, "
          f"{len(catalog['cards'])} cards, {len(catalog['references'])} references, "
          f"{len(catalog['tokens'])} tokens")


if __name__ == "__main__":
    main()
