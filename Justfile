# Build Anki decks (.apkg) from der|die|das vocabulary HTML pages.
# Recipes run the script through the flake's Python env (genanki + beautifulsoup4).

# List available recipes.
default:
    @just --list

# Build a deck from one HTML file, e.g. `just build v11.html`.
build vocab *args:
    nix develop --command python derdiedas_to_anki.py --vocab {{vocab}} {{args}}

# Build decks from every v*.html file into a subfolder (default: decks/).
all dir="decks":
    nix develop --command bash -c 'for f in v*.html; do python derdiedas_to_anki.py --vocab "$f" --output "{{dir}}/$(basename "$f" .html).apkg"; done'

# Remove generated .apkg files.
clean:
    rm -f *.apkg decks/*.apkg
