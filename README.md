# Frontier Tabletop Simulator assets

The [Game components slice in Figma](https://www.figma.com/design/Pe6o98Z2YYYgNB8kH33Pgl/Frontier?node-id=218-13798) defines the playable export set. The static catalog is in `docs/`; publish that folder with GitHub Pages. It provides direct PNG links for Tabletop Simulator and deck import settings.

Current export:

| Deck | Cards | Width | Height | Back |
| --- | ---: | ---: | ---: | --- |
| Monuments | 32 | 8 | 4 | Monument card back |
| Objectives | 30 | 6 | 5 | Objective card back |
| Specials | 16 | 4 | 4 | Special Card back |

There are also 3 boards, 2 standalone guide cards, and 12 tokens. Each deck sheet has no spacing between card bounds. Set **Back is Hidden** on when importing a deck into TTS.

## Refreshing the exports

1. Render the current contents of the Figma slice into `tmp/figma-export/`. Export grouped card frames at their natural size with no page overlays; export each board, back, guide, and token individually. The Figma node IDs and names are recorded in `docs/catalog.json`.
2. Run `scripts/build_assets.py` with Python and Pillow. This packs the card groups, copies individual assets, and regenerates `docs/catalog.json` and `docs/catalog.js`.
3. Review the deck previews and counts, then commit and push `docs/` to GitHub. GitHub Pages serves the landing page and image files.

The builder uses content hashes in published PNG filenames. It retains older PNGs so links already saved in TTS continue to work after artwork updates. The Special back in Figma is 388 × 519 while its face cards are 442 × 640; the builder scales that back to 442 × 640 for TTS.
