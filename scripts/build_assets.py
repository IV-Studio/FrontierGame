"""Pack Figma Game components exports into Tabletop Simulator images.

Input screenshots go in tmp/figma-export/. Run this after refreshing those
screenshots from the current Figma slice. Existing hashed files are retained so
saved Tabletop Simulator games keep working after a new export.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tmp" / "figma-export"
ASSETS = ROOT / "docs" / "assets"
DOCS = ROOT / "docs"


def publish(image: Image.Image, category: str, slug: str) -> dict:
    from io import BytesIO

    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    buffer = BytesIO()
    image.save(buffer, "PNG", optimize=True)
    data = buffer.getvalue()
    digest = hashlib.sha256(data).hexdigest()[:10]
    directory = ASSETS / category
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}-{digest}.png"
    path = directory / filename
    if not path.exists():
        path.write_bytes(data)
    return {"path": f"assets/{category}/{filename}", "width": image.width, "height": image.height}


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
    catalog = {"source": "Figma Game components slice 218:13798", "boards": [],
               "cards": [], "decks": [], "tokens": []}

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

    manifest = json.dumps(catalog, indent=2, ensure_ascii=False)
    (DOCS / "catalog.json").write_text(manifest + "\n", encoding="utf-8")
    (DOCS / "catalog.js").write_text("window.FRONTIER_CATALOG = " +
                                      json.dumps(catalog, ensure_ascii=False) + ";\n",
                                      encoding="utf-8")
    print(f"Built {len(catalog['decks'])} decks, {len(catalog['boards'])} boards, "
          f"{len(catalog['cards'])} cards, {len(catalog['tokens'])} tokens")


if __name__ == "__main__":
    main()
