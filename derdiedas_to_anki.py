#!/usr/bin/env python3
"""Build one Anki deck (.apkg) per chapter from der|die|das vocabulary JSON.

Usage:
    python derdiedas_to_anki.py --vocab vocab/k1.json vocab/k2.json ... [--outdir decks]

Reads the site's API JSON (see `just fetch`) and writes <outdir>/kapitel-<n>.apkg
for each `kapitel` found in the entries.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import genanki

# Fixed model id so re-imports update the same note type rather than duplicating it.
MODEL_ID = 1740123456
MODEL = genanki.Model(
    MODEL_ID,
    "der die das Vocab (DE->EN)",
    fields=[
        {"name": "German"},
        {"name": "Translation"},
        {"name": "Forms"},
    ],
    templates=[
        {
            "name": "DE->EN",
            "qfmt": '<div class="german">{{German}}</div>',
            "afmt": (
                '{{FrontSide}}<hr id="answer">'
                '<div class="translation">{{Translation}}</div>'
                "{{#Forms}}<div class=\"forms\">{{Forms}}</div>{{/Forms}}"
            ),
        }
    ],
    css="""
.card { font-family: Georgia, "Times New Roman", serif; font-size: 22px;
        text-align: center; color: #222; background: #fff; }
.german { font-weight: bold; }
.translation { margin-top: 8px; }
.forms { margin-top: 8px; color: #666; font-size: 18px; font-style: italic; }
""",
)

# Chapter titles aren't in the API JSON, so they're listed here
# (taken from the dddgerman.org home page).
CHAPTER_TITLES = {
    1: "Smalltalk",
    2: "Vernetzt",
    3: "Sonntag",
    4: "Mahlzeit",
    5: "Autobahn",
    6: "Heimat",
    7: "Sportsachen",
    8: "Großstadt",
    9: "Mallorca",
    10: "Kindheit",
    11: "Bildung",
    12: "Grenzen",
    13: "Berlin",
    14: "Geld",
    15: "Natur",
    16: "Amerika",
}


def deck_name_for(chapter):
    title = CHAPTER_TITLES.get(chapter)
    return f"Kapitel {chapter}: {title}" if title else f"Kapitel {chapter}"


def forms_for(entry):
    """Plural, plus verb forms ('stemChange | simplePast | pastPart') when present."""
    parts = []
    if entry.get("pluralNoun"):
        parts.append(entry["pluralNoun"].strip())
    if entry.get("simplePast"):
        verb = [entry.get("stemChange"), entry["simplePast"], entry.get("pastPart")]
        parts.append(" | ".join(v.strip() for v in verb if v and v.strip()))
    return " · ".join(parts)


def parse_entry(entry):
    """Return (thema, word, german, translation_html, forms) for one entry, or None."""
    word = (entry.get("word") or "").strip()
    translation = (entry.get("translation") or "").strip()
    if not word or not translation:
        return None

    article = (entry.get("article") or "").strip()
    german = f"{article} {word}" if article else word
    return entry.get("thema"), word, german, translation, forms_for(entry)


def build_deck(chapter, rows):
    """Build one deck from parsed entries; return (deck, name, count, skipped)."""
    name = deck_name_for(chapter)
    # hashlib, not hash(): the id must be stable across runs.
    deck_id = int(hashlib.sha1(name.encode()).hexdigest(), 16) % 10**10
    deck = genanki.Deck(deck_id, name)

    seen = set()
    count = skipped = 0
    # Sort for deterministic output (thema may be null -> sorts first).
    for thema, word, german, translation, forms in sorted(
        rows, key=lambda r: (r[0] or 0, r[1].lower())
    ):
        guid = genanki.guid_for(german, translation)
        if guid in seen:
            skipped += 1
            continue
        seen.add(guid)
        deck.add_note(
            genanki.Note(
                model=MODEL,
                fields=[german, translation, forms],
                guid=guid,
                tags=[f"thema-{thema}"],
            )
        )
        count += 1

    return deck, name, count, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vocab", required=True, nargs="+", help="paths to the vocab JSON files"
    )
    parser.add_argument(
        "--outdir", default="decks", help="output directory (default: decks)"
    )
    args = parser.parse_args(argv)

    chapters = {}
    for vocab in args.vocab:
        json_path = Path(vocab)
        if not json_path.is_file():
            raise SystemExit(f"File not found: {json_path}")
        for entry in json.loads(json_path.read_text(encoding="utf-8")):
            row = parse_entry(entry)
            if row is not None:
                chapters.setdefault(entry["kapitel"], []).append(row)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for chapter in sorted(chapters):
        deck, name, count, skipped = build_deck(chapter, chapters[chapter])
        output = outdir / f"kapitel-{chapter}.apkg"
        genanki.Package(deck).write_to_file(str(output))
        extra = f", {skipped} duplicates skipped" if skipped else ""
        print(f"{count} cards -> {output} (deck: {name}{extra})")


if __name__ == "__main__":
    sys.exit(main())
