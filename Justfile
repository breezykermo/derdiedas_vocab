# Build Anki decks (.apkg) from der|die|das vocabulary JSON.
# Recipes run the script through the flake's Python env (genanki; curl for fetch).

# List available recipes.
default:
    @just --list

# Download all 16 chapters into vocab/. Needs DDD_JWT: log in at dddgerman.org, then in the
# Firefox console run copy(localStorage.getItem("DDD_JWT")) and `export DDD_JWT=<paste>`.
fetch:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -z "${DDD_JWT:-}" ]; then
        echo "DDD_JWT is not set; see the comment above this recipe (or the README)" >&2
        exit 1
    fi
    mkdir -p vocab
    for k in $(seq 1 16); do
        tmp=$(mktemp)
        if ! nix develop --command bash -c 'curl -sf -H "Authorization: Bearer $DDD_JWT" "https://api.dddgerman.org/api/vocab/$0" | python -m json.tool --no-ensure-ascii --indent 1' "$k" > "$tmp"; then
            rm -f "$tmp"
            echo "fetching chapter $k failed (expired DDD_JWT?)" >&2
            exit 1
        fi
        mv "$tmp" "vocab/k$k.json"
        echo "vocab/k$k.json"
    done

# Build chapter decks from the given JSON files, e.g. `just build vocab/k1.json`.
build *files:
    nix develop --command python derdiedas_to_anki.py --vocab {{files}}

# Build one deck per chapter from every vocab/*.json file into a subfolder (default: decks/).
all dir="decks":
    nix develop --command bash -c 'python derdiedas_to_anki.py --vocab vocab/*.json --outdir "{{dir}}"'

# Remove generated .apkg files.
clean:
    rm -f *.apkg decks/*.apkg
