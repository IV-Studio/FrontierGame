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
# The six newly added Page 5 Monuments have small manual x offsets.
CARD_X_OFFSETS = {"monuments": {26: 4, 27: 4, 28: 8, 29: 8}}


class Publisher:
    """Keep the catalog URL and all previously issued URLs current."""

    def __init__(self, assets: Path = ASSETS, archive: Path = ARCHIVE,
                 catalog_path: Path = DOCS / "catalog.json") -> None:
        self.assets = assets
        self.archive = archive
        self.active_paths: set[Path] = set()
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
        self.active_paths.update(aliases)

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
                "width": image.width, "height": image.height,
                "revision": hashlib.sha256(data).hexdigest()[:10]}

    def retire_unlisted(self) -> list[str]:
        """Archive and remove published PNGs absent from the current slice."""
        retired = []
        for path in sorted(self.assets.glob("*/*.png")):
            if path in self.active_paths:
                continue
            category = path.parent.name
            match = re.fullmatch(r"(.+?)(?:-[0-9a-f]{10})?\.png", path.name)
            if not match:
                raise ValueError(f"Unexpected asset filename: {path}")
            slug = match.group(1)
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()[:12]
            saved = self.archive / category / slug / f"{digest}.png"
            saved.parent.mkdir(parents=True, exist_ok=True)
            if saved.exists() and saved.read_bytes() != data:
                raise ValueError(f"Archive hash collision: {saved}")
            if not saved.exists():
                saved.write_bytes(data)
            path.unlink()
            retired.append(f"{category}/{path.name}")
        return retired


def load(name: str) -> Image.Image:
    path = SOURCE / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing Figma export: {path}")
    return Image.open(path)


def sheet(name: str, count: int, source_columns: int, origin: tuple[int, int],
          stride: tuple[int, int], card_size: tuple[int, int],
          columns: int, rows: int, start: int = 0) -> dict:
    image = load(name)
    mode = "RGBA" if "A" in image.getbands() else "RGB"
    result = Image.new(mode, (columns * card_size[0], rows * card_size[1]))
    for index in range(count):
        source_index = start + index
        source_col = source_index % source_columns
        source_row = source_index // source_columns
        x = origin[0] + source_col * stride[0] + CARD_X_OFFSETS.get(name, {}).get(source_index, 0)
        y = origin[1] + source_row * stride[1]
        box = (x, y, x + card_size[0], y + card_size[1])
        if box[2] > image.width or box[3] > image.height:
            raise ValueError(f"Card {index + 1} falls outside {name} export")
        card = image.crop(box)
        result.paste(card, ((index % columns) * card_size[0],
                            (index // columns) * card_size[1]))
    return {"image": result, "count": count, "columns": columns,
            "rows": rows, "cardWidth": card_size[0], "cardHeight": card_size[1]}


def individual_sheet(name: str, count: int, columns: int, rows: int,
                     card_size: tuple[int, int]) -> dict:
    """Pack individually exported cards without downscaling a large Figma frame."""
    result = Image.new("RGBA", (columns * card_size[0], rows * card_size[1]))
    for index in range(count):
        card = load(f"{name}-card-{index + 1:02d}").convert("RGBA")
        if card.size != card_size:
            raise ValueError(f"Unexpected {name} card {index + 1} size: {card.size}")
        result.paste(card, ((index % columns) * card_size[0],
                            (index // columns) * card_size[1]))
    return {"image": result, "count": count, "columns": columns,
            "rows": rows, "cardWidth": card_size[0], "cardHeight": card_size[1]}


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    publish = Publisher()
    catalog = {"source": "Figma Page 5 Game components slice 400:5081", "boards": [],
               "cards": [], "references": [], "decks": [], "tokens": []}

    for slug, title, figma_id in [
        ("board-main", "Main board", "400:5197"),
    ]:
        catalog["boards"].append({"title": title, "figmaId": figma_id,
                                   **publish(load(slug), "boards", slug)})

    for slug, title, figma_id in [
        ("card-action-guide", "Action Guide", "400:3386"),
        ("card-region-bonus-guide", "Region Bonus Guide", "400:3436"),
    ]:
        catalog["cards"].append({"title": title, "figmaId": figma_id,
                                  **publish(load(slug), "cards", slug)})

    deck_specs = [
        ("monuments", "monuments", "Monuments", "400:4331", 30, 6, (0, 0), (482, 680),
         (442, 640), 6, 5, "back-monument", 0),
        ("objectives", "objectives", "Objectives", "400:3464", 18, 6, (196, 140), (420, 551),
         (388, 519), 6, 3, "back-objective", 0),
        ("specials", "specials", "Specials", "400:4909", 24, 4, (0, 0), (482, 680),
         (442, 640), 4, 6, "back-special", 0),
    ]
    for (slug, asset_slug, title, figma_id, count, source_columns, origin, stride,
         card_size, columns, rows, back_slug, start) in deck_specs:
        packed = (individual_sheet("special", count, columns, rows, card_size)
                  if slug == "specials" else
                  sheet(slug, count, source_columns, origin, stride,
                        card_size, columns, rows, start))
        face = publish(packed.pop("image"), "decks", f"{asset_slug}-faces")
        back = load(back_slug)
        if back.size != card_size:
            # TTS applies the same card geometry to both sides.
            back = back.resize(card_size, Image.Resampling.LANCZOS)
        back_asset = publish(back, "decks", f"{asset_slug}-back")
        catalog["decks"].append({"title": title, "figmaId": figma_id,
                                  **packed, "face": face, "back": back_asset})

    action_tiles = [
        ("action-tile-1", "Build 4", "400:3302", "page5-tile-3302"),
        ("action-tile-2", "Region bonus", "400:3383", "page5-tile-3383"),
        ("action-tile-3", "Build 3", "400:3254", "page5-tile-3254"),
        ("action-tile-4", "Build 4, four regions", "400:3351", "page5-tile-3351"),
        ("action-tile-5", "+1", "400:3374", "page5-tile-3374"),
        ("action-tile-6", "+2", "400:3377", "page5-tile-3377"),
        ("action-tile-7", "Build 2, four regions", "400:3232", "page5-tile-3232"),
        ("action-tile-8", "+3", "400:3380", "page5-tile-3380"),
        ("action-tile-9", "Move", "400:3276", "page5-tile-3276"),
        ("action-tile-10", "Build 6", "400:3324", "page5-tile-3324"),
    ]
    for slug, title, figma_id, source in action_tiles:
        catalog["tokens"].append({"title": title,
                                  "figmaId": figma_id,
                                  **publish(load(source), "tokens", slug)})

    retired = publish.retire_unlisted()

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
          f"{len(catalog['tokens'])} tokens; retired {len(retired)} old images")


if __name__ == "__main__":
    main()
