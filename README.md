# Frontier Tabletop Simulator assets

The [Page 8 Game components slice in Figma](https://www.figma.com/design/Pe6o98Z2YYYgNB8kH33Pgl/Frontier?node-id=714-2102) defines the playable export set. The static catalog is in `docs/`; GitHub Pages publishes that folder. It provides direct PNG links for Tabletop Simulator and deck import settings.

Current export:

| Deck | Cards | Width | Height | Back |
| --- | ---: | ---: | ---: | --- |
| Monuments | 30 | 6 | 5 | Monument card back |
| Objectives | 18 | 6 | 3 | Objective card back |
| Specials | 19 | 6 | 4 | Special Card back |

Supplemental dice and branched actions remain from Page 7. Towered objective sets of 2, 3, 4, and 5 award 3, 5, 8, and 12 VP. The monument deck uses the Page 7 set copied onto Page 8.

There is one main board, two standalone guide cards, fourteen dice textures, twenty-two action tiles, and fourteen branched actions. Each deck sheet has no spacing between card bounds. Set **Back is Hidden** on when importing a deck into TTS. Existing Special decks need Width 6, Height 4, and Number 19 after this update.

## Refreshing the exports

1. Render the current contents of the Figma slice into `tmp/figma-export/`. Export monument and objective frames, each special card, the board, backs, guides, dice, action tiles, and branched actions. The Figma node IDs and names are recorded in `docs/catalog.json` and `scripts/build_assets.py`.
2. Run `scripts/build_assets.py` with Python and Pillow. This packs the card groups, copies individual assets, and regenerates `docs/catalog.json` and `docs/catalog.js`.
3. Review the deck previews and counts, then commit and push `docs/` and `archive/` to GitHub. GitHub Pages serves the landing page and current image files.

The builder keeps every **active** PNG URL stable. Before replacing an image, it saves its old bytes under `archive/assets/<category>/<slug>/<content-hash>.png`. All historical aliases for an active asset receive the same new image. Images absent from the current Figma slice are archived and removed from the site. Commit the archive and site together so GitHub Pages deploys them from one Git commit. GitHub Pages and TTS may cache images, so an open TTS game may need to be reloaded after deployment.

The Special back in Figma is 388 × 519 while its face cards are 443 × 704; the builder scales that back to 443 × 704 for TTS.
