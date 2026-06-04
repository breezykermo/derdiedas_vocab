# derdiedas → Anki

Turn a [der | die | das](https://dddgerman.org) **Wortschatz** (vocabulary) page
into an Anki deck (`.apkg`) of German → English cards.

## 1. Save the page

1. Open the chapter's **Wortschatz** page in your browser.
2. Save it to this folder as an HTML file: **File → Save Page As…** (or `Ctrl/Cmd+S`),
   choosing *"Web Page, Complete"*. Name it something like `v11.html`.

The script reads the vocabulary list from the saved HTML; you don't need the
accompanying `_files/` folder.

## 2. Build the deck

Requires [Nix](https://nixos.org) (with flakes) and [just](https://github.com/casey/just).

```bash
just build v11.html       # -> v11.apkg
just all                  # build every v*.html into decks/
just clean                # remove generated .apkg files
```

Each deck is named after the page header, e.g. `Kapitel 1: Thema 1`.

Without `just`, run the script directly through the flake:

```bash
nix develop --command python derdiedas_to_anki.py --vocab v11.html [--output v11.apkg]
# or:
nix run . -- --vocab v11.html
```

## 3. Import into Anki

Double-click the generated `.apkg` (or **File → Import** in Anki). Re-running the
script and re-importing updates the existing deck/notes rather than duplicating them.
