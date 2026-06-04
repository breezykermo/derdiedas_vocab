#!/usr/bin/env python3
"""Build an Anki deck (.apkg) from a der|die|das vocabulary HTML page.

Usage:
    python derdiedas_to_anki.py --vocab v11.html [--output v11.apkg]
"""
import argparse
import sys
from pathlib import Path

import genanki
from bs4 import BeautifulSoup, NavigableString

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


def _has_classes(tag, *names):
    classes = tag.get("class", [])
    return all(n in classes for n in names)


def find_vocab_container(soup):
    """The vocab list is the div carrying both `w-10/12` and `divide-y`."""
    for div in soup.find_all("div"):
        if _has_classes(div, "w-10/12", "divide-y"):
            return div
    return None


def deck_name_for(soup, fallback):
    """Use the header's <h4> (e.g. 'KAPITEL 1: THEMA 1' -> 'Kapitel 1: Thema 1')."""
    h4 = soup.find("h4")
    if h4 and h4.get_text(strip=True):
        return h4.get_text(strip=True).title()
    return fallback


def inner_html(tag):
    return "".join(str(c) for c in tag.children).strip()


def parse_row(row):
    """Return (german, translation_html, forms) for one `div.py-2`, or None."""
    span = row.find("span", recursive=False)
    if span is None:
        return None

    word_tag = span.find("span", class_="cursor-pointer")
    translation_tag = span.find("span", class_="translation")
    if word_tag is None or translation_tag is None:
        return None

    word = word_tag.get_text(strip=True)
    translation = inner_html(translation_tag)
    if not word or not translation:
        return None

    # Article = leading text node(s) before the word span.
    article = ""
    for child in span.children:
        if child is word_tag:
            break
        if isinstance(child, NavigableString):
            article += str(child)
    article = article.strip()

    german = f"{article} {word}".strip() if article else word

    # Forms = the plain <span>s between the word span and the translation span.
    forms = []
    for sib in word_tag.find_next_siblings("span"):
        if sib is translation_tag:
            break
        text = sib.get_text(strip=True).strip("[]").strip()
        if text:
            forms.append(text)
    forms_text = " · ".join(forms)

    return german, translation, forms_text


def build_deck(html_path):
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")

    container = find_vocab_container(soup)
    if container is None:
        raise SystemExit(
            f"No vocab container (div.w-10/12.divide-y) found in {html_path}"
        )

    name = deck_name_for(soup, html_path.stem)
    deck = genanki.Deck(abs(hash(name)) % (10 ** 10), name)

    count = 0
    for row in container.find_all("div", class_="py-2"):
        parsed = parse_row(row)
        if parsed is None:
            continue
        german, translation, forms = parsed
        note = genanki.Note(
            model=MODEL,
            fields=[german, translation, forms],
            guid=genanki.guid_for(name, german, translation),
        )
        deck.add_note(note)
        count += 1

    return deck, name, count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocab", required=True, help="path to the vocab HTML file")
    parser.add_argument("--output", help="output .apkg path (default: <vocab>.apkg)")
    args = parser.parse_args(argv)

    html_path = Path(args.vocab)
    if not html_path.is_file():
        raise SystemExit(f"File not found: {html_path}")

    output = Path(args.output) if args.output else html_path.with_suffix(".apkg")

    deck, name, count = build_deck(html_path)
    if count == 0:
        raise SystemExit(f"No vocabulary entries found in {html_path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(deck).write_to_file(str(output))
    print(f"{count} cards -> {output} (deck: {name})")


if __name__ == "__main__":
    sys.exit(main())
