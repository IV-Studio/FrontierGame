from __future__ import annotations

import csv
import math
import random
import zipfile
from collections import Counter
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf"
PNG_DIR = OUT / "objective_cards_png"
PDF_PATH = OUT / "frontier_objective_cards.pdf"
CSV_PATH = OUT / "frontier_objective_cards_manifest.csv"
ZIP_PATH = OUT / "frontier_objective_cards_png.zip"

CARD_W_IN = 2.5
CARD_H_IN = 3.5
PNG_W = 750
PNG_H = 1050

BG = "#696A68"
FRAME = "#30312E"
PAPER = "#EFE9DA"

REGIONS = {
    "Frostlands": ("#BDBBB0", ["Silverlake", "Frostpeak", "Northwatch", "Glacierfall"]),
    "Red Frontier": ("#C66E3E", ["Redmoore", "Ironholt", "Westgate", "Highridge", "Stonefield"]),
    "Coast": ("#72AAA5", ["Seabreeze", "Coralbay", "Tidewatch"]),
    "Heartland": ("#B99B68", ["Eldenwood", "Oakridge", "Meadowbrook"]),
    "Sunlands": ("#CB9547", ["Sunvale", "Brightwood"]),
    "Green March": ("#A6A768", ["Aridale", "Dustmere", "Stonehollow"]),
}

LOCATIONS = []
for region, (color, names) in REGIONS.items():
    for name in names:
        LOCATIONS.append({"name": name, "region": region, "color": color})

BY_NAME = {item["name"]: item for item in LOCATIONS}


def pick_exact_cards(size: int, targets: dict[str, int], seed: int) -> list[tuple[str, ...]]:
    """Find unique, cross-region cards matching exact location degree targets."""
    all_cards = [
        combo
        for combo in combinations([x["name"] for x in LOCATIONS], size)
        if len({BY_NAME[name]["region"] for name in combo}) == size
    ]
    rng = random.Random(seed)
    for _ in range(5000):
        remaining = targets.copy()
        chosen: list[tuple[str, ...]] = []
        available = set(all_cards)
        while sum(remaining.values()):
            candidates = [
                card for card in available
                if all(remaining[name] > 0 for name in card)
            ]
            if not candidates:
                break
            rng.shuffle(candidates)
            candidates.sort(
                key=lambda card: (
                    sum(remaining[name] ** 2 for name in card),
                    sum(remaining[name] for name in card),
                ),
                reverse=True,
            )
            card = rng.choice(candidates[: min(14, len(candidates))])
            chosen.append(card)
            available.remove(card)
            for name in card:
                remaining[name] -= 1
        if not any(remaining.values()) and len(chosen) == 25:
            return chosen
    raise RuntimeError(f"Could not construct {size}-location objective set")


def build_deck() -> list[dict]:
    names = [x["name"] for x in LOCATIONS]
    pair_targets = {name: (3 if i < 10 else 2) for i, name in enumerate(names)}
    triple_targets = {
        name: (3 if i < 5 else 4)
        for i, name in enumerate(names)
    }
    pairs = pick_exact_cards(2, pair_targets, 4302)
    triples = pick_exact_cards(3, triple_targets, 8808)
    return [
        *[{"points": 4, "locations": card} for card in pairs],
        *[{"points": 8, "locations": card} for card in triples],
    ]


def fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: str, max_size: int, max_width: int):
    for size in range(max_size, 22, -2):
        font = ImageFont.truetype(font_path, size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return ImageFont.truetype(font_path, 22)


def draw_ticket_png(draw: ImageDraw.ImageDraw, box, fill, label, font_path):
    x0, y0, x1, y1 = box
    outline = 9
    radius = 22
    draw.rounded_rectangle(box, radius=radius, fill=FRAME, outline=FRAME)
    inner = (x0 + outline, y0 + outline, x1 - outline, y1 - outline)
    draw.rounded_rectangle(inner, radius=radius - 6, fill=fill)
    # Side notches create the same clipped-ticket feel as the supplied concept.
    notch = 17
    for x in (x0, x1):
        for y in (y0 + 16, y1 - 16):
            draw.ellipse((x - notch, y - notch, x + notch, y + notch), fill=BG)
    font = fit_font(draw, label, font_path, 48, int((x1 - x0) * 0.82))
    bbox = draw.textbbox((0, 0), label, font=font)
    tx = (x0 + x1 - (bbox[2] - bbox[0])) / 2
    ty = (y0 + y1 - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((tx, ty), label, font=font, fill="#11110F")


def render_card_png(card: dict, card_no: int, path: Path, font_serif: str, font_sans_bold: str):
    img = Image.new("RGB", (PNG_W, PNG_H), PAPER)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((24, 24, PNG_W - 24, PNG_H - 24), radius=42, fill=FRAME)
    draw.rounded_rectangle((45, 45, PNG_W - 45, PNG_H - 45), radius=29, fill=BG)
    draw.rounded_rectangle((62, 62, PNG_W - 62, PNG_H - 62), radius=22, outline="#858681", width=3)

    cx, cy, r = PNG_W // 2, 143, 63
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#F5F3EE", outline="#10110F", width=9)
    pts_font = ImageFont.truetype(font_sans_bold, 77)
    pts = str(card["points"])
    box = draw.textbbox((0, 0), pts, font=pts_font)
    draw.text((cx - (box[2] - box[0]) / 2, cy - (box[3] - box[1]) / 2 - box[1]), pts, font=pts_font, fill="#050505")

    count = len(card["locations"])
    ticket_h = 145 if count == 2 else 132
    gap = 38 if count == 2 else 30
    total_h = count * ticket_h + (count - 1) * gap
    start_y = 280 + (550 - total_h) // 2
    for i, name in enumerate(card["locations"]):
        y = start_y + i * (ticket_h + gap)
        draw_ticket_png(draw, (105, y, PNG_W - 105, y + ticket_h), BY_NAME[name]["color"], name, font_serif)

    small = ImageFont.truetype(font_sans_bold, 20)
    footer = f"OBJECTIVE  {card_no:02d}"
    box = draw.textbbox((0, 0), footer, font=small)
    draw.text(((PNG_W - (box[2] - box[0])) / 2, PNG_H - 82), footer, font=small, fill="#D0D0C9")
    img.save(path, quality=95, dpi=(300, 300))


def make_pdf(deck: list[dict], png_paths: list[Path]):
    page_w, page_h = letter
    card_w = CARD_W_IN * 72
    card_h = CARD_H_IN * 72
    cols, rows = 3, 2
    grid_w, grid_h = cols * card_w, rows * card_h
    margin_x = (page_w - grid_w) / 2
    margin_y = (page_h - grid_h) / 2
    c = canvas.Canvas(str(PDF_PATH), pagesize=letter)
    c.setTitle("Frontier Objective Cards")
    for idx, png_path in enumerate(png_paths):
        slot = idx % (cols * rows)
        if slot == 0:
            c.setFillColor(HexColor("#FFFFFF"))
            c.rect(0, 0, page_w, page_h, stroke=0, fill=1)
        col = slot % cols
        row = slot // cols
        x = margin_x + col * card_w
        y = page_h - margin_y - (row + 1) * card_h
        c.drawImage(str(png_path), x, y, width=card_w, height=card_h, mask="auto")
        # Hairline cut guides sit outside the artwork edge.
        c.setStrokeColor(HexColor("#9A9A9A"))
        c.setLineWidth(0.25)
        tick = 7
        for px, sx in ((x, -1), (x + card_w, 1)):
            c.line(px, y - tick, px, y)
            c.line(px, y + card_h, px, y + card_h + tick)
        for py, sy in ((y, -1), (y + card_h, 1)):
            c.line(x - tick, py, x, py)
            c.line(x + card_w, py, x + card_w + tick, py)
        if slot == cols * rows - 1 or idx == len(png_paths) - 1:
            c.setFillColor(HexColor("#666666"))
            c.setFont("Helvetica", 7)
            c.drawCentredString(page_w / 2, 15, "Frontier Objective Cards - print at 100% / actual size")
            c.showPage()
    c.save()


def validate(deck: list[dict]):
    assert len(deck) == 50
    assert sum(card["points"] == 4 for card in deck) == 25
    assert sum(card["points"] == 8 for card in deck) == 25
    assert len({tuple(sorted(card["locations"])) for card in deck}) == 50
    counts = Counter(name for card in deck for name in card["locations"])
    assert set(counts.values()) <= {6, 7}, counts
    for card in deck:
        assert len({BY_NAME[name]["region"] for name in card["locations"]}) == len(card["locations"])
    return counts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    serif = r"C:\Windows\Fonts\georgiab.ttf"
    sans_bold = r"C:\Windows\Fonts\arialbd.ttf"
    deck = build_deck()
    counts = validate(deck)

    png_paths = []
    for idx, card in enumerate(deck, 1):
        path = PNG_DIR / f"objective_{idx:02d}_{card['points']}pt.png"
        render_card_png(card, idx, path, serif, sans_bold)
        png_paths.append(path)

    make_pdf(deck, png_paths)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["card", "points", "location_1", "location_2", "location_3"])
        for idx, card in enumerate(deck, 1):
            writer.writerow([idx, card["points"], *card["locations"], *([""] * (3 - len(card["locations"])))])

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in png_paths:
            archive.write(path, arcname=path.name)

    print(f"Created: {PDF_PATH}")
    print(f"Created: {CSV_PATH}")
    print(f"Created: {ZIP_PATH}")
    print("Location counts:")
    for name in sorted(counts):
        print(f"  {name}: {counts[name]}")


if __name__ == "__main__":
    main()
