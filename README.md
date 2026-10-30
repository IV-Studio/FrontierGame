# Frontier Tabletop Simulator assets

The [Page 4 Game Components slice in Figma](https://www.figma.com/design/Pe6o98Z2YYYgNB8kH33Pgl/Frontier?node-id=339-5632) defines the playable export set. The static catalog is in `docs/`; GitHub Pages publishes that folder. It provides direct PNG links for Tabletop Simulator and deck import settings.

Current export:

| Deck | Cards | Width | Height | Back |
| --- | ---: | ---: | ---: | --- |
| Monuments | 24 | 6 | 4 | Monument card back |
| Objectives | 18 | 6 | 3 | Objective card back |
| Specials | 24 | 4 | 6 | Special Card back |

There is one main board, two standalone guide cards, and ten action tiles. The previous main board is replaced at its existing URL; The Edge is retired from the catalog. Each deck sheet has no spacing between card bounds. Set **Back is Hidden** on when importing a deck into TTS.

## Refreshing the exports

1. Render the current contents of the Figma slice into `tmp/figma-export/`. Export monument and objective frames, each special card, the board, backs, guides, and action tiles. The Figma node IDs and names are recorded in `docs/catalog.json` and `scripts/build_assets.py`.
2. Run `scripts/build_assets.py` with Python and Pillow. This packs the card groups, copies individual assets, and regenerates `docs/catalog.json` and `docs/catalog.js`.
3. Review the deck previews and counts, then commit and push `docs/` and `archive/` to GitHub. GitHub Pages serves the landing page and current image files.

The builder keeps every previously published PNG URL stable. Before replacing an image, it saves its old bytes under `archive/assets/<category>/<slug>/<content-hash>.png`. This includes older hashed URLs that may already be used in TTS. The current catalog keeps its existing URLs, and all historical aliases for an asset receive the same new image. Commit the archive and overwritten assets together so GitHub Pages deploys them from one Git commit. GitHub Pages and TTS may cache images, so an open TTS game may need to be reloaded after deployment.

The Special back in Figma is 388 × 519 while its face cards are 442 × 640; the builder scales that back to 442 × 640 for TTS.
