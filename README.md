# derdiedas → Anki

Turn [der | die | das](https://dddgerman.org) **Wortschatz** (vocabulary)
into Anki decks (`.apkg`) of German → English cards, one deck per chapter.

## 1. Fetch the vocabulary

The script reads the site's API JSON, one file per chapter in `vocab/`
(already checked in; refresh it when the site changes). Fetching needs your
login token: log in at dddgerman.org, open the Firefox console and run

```js
copy(localStorage.getItem("DDD_JWT"))
```

then export it and fetch all 16 chapters:

```bash
export DDD_JWT=<paste>
just fetch                     # -> vocab/k1.json .. vocab/k16.json
```

The old saved `v*.html` pages are no longer used.

## 2. Build the decks

Requires [Nix](https://nixos.org) (with flakes) and [just](https://github.com/casey/just).

```bash
just all                       # build every vocab/*.json into decks/
just build vocab/k1.json       # -> decks/kapitel-1.apkg
just clean                     # remove generated .apkg files
```

Entries are grouped by their `kapitel`, so all the Themen of a chapter end up
in one deck, e.g. `Kapitel 1: Smalltalk`. Each note is tagged with its thema
(`thema-3`), so you can still filter by Thema in Anki. Chapter titles aren't in
the JSON, so the script carries the 16 titles from the dddgerman.org home page
in `CHAPTER_TITLES`.

Without `just`, run the script directly through the flake:

```bash
nix develop --command python derdiedas_to_anki.py --vocab vocab/k1.json [--outdir decks]
# or:
nix run . -- --vocab vocab/k1.json
```

## 3. Import into Anki

Double-click the generated `.apkg` (or **File → Import** in Anki). Re-running the
script and re-importing updates the existing deck/notes rather than duplicating them.

If you imported the old per-thema decks (`Kapitel 1: Thema 1` etc.), delete them
in Anki after importing the new chapter deck: the note GUIDs changed, so they
won't be updated in place.

## 4. Podcast and speaking prompts

`podcasts/kapitel-N.txt` (NotebookLM Audio Overview sources) and
`speaking/kapitel-N.txt` (voice practice with Claude) are generated from
`vocab/` plus the course's grammar slides in `course/`:

```bash
just prompts
```

Each prompt holds the conversation to what's known by the end of chapter N:
the cumulative vocabulary lists, the grammar of chapters 1–N, and a
**NOT YET LEARNED** section listing later grammar (`MILESTONES` in
`make_prompts.py`) and everyday words (`EVERYDAY_WORDS`) whose chapter is
looked up in the vocab, e.g. `in`/`auf` until chapter 7, `weil`/`dass` until 10.
