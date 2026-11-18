"""Generate podcasts/ (NotebookLM) and speaking/ (Claude) kapitel-N.txt sources from vocab JSON + slides."""
import html
import json
import re
import textwrap
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent   # reads vocab/ and course/, writes podcasts/ and speaking/
API = REPO / "course"                    # themas.json, kapitels.json, slides/sN-T.json

# Everyday words a model reaches for without thinking. Each is held back until the chapter whose
# vocabulary list introduces it, and listed as NOT YET LEARNED before then (e.g. `in`, `auf` until
# Kapitel 7, `weil`, `dass` until Kapitel 10).
EVERYDAY_WORDS = """
mit zu von bei nach aus seit gegenüber für ohne gegen durch um bis in auf an über unter vor hinter
neben zwischen während wegen trotz statt
denn sondern weil dass wenn ob als bevor nachdem damit obwohl
können müssen wollen sollen dürfen mögen wissen kennen lassen bleiben geben sehen werden
noch schon nie oft dort dann mehr so also wieder zusammen nichts alles jemand niemand doch
wer wann warum welch- dies- jed- gleich zuerst früher leider vielleicht natürlich wirklich
besonders eigentlich ziemlich fast genau richtig falsch toll Fehler Beispiel Regel
""".split()

# Grammar milestones as (kapitel taught, what to avoid before then), checked against the course's
# Strukturen headings. Everything at or below the current chapter is allowed.
MILESTONES = [
    (2, "grammatical case and its terms; negation with kein; possessives (mein, dein ...); "
        "man; welch-/dies-/jed-; werden"),
    (3, "stem-changing verbs (du fährst, er liest); separable verbs (ich stehe auf); "
        "adjective endings; the past with war/hatte"),
    (4, "the accusative case (einen, den, ihn); accusative prepositions (für, ohne, gegen, durch, um); "
        "es gibt; mögen"),
    (5, "the Perfekt (ich habe gemacht, ich bin gefahren) and any past tense beyond war/hatte; "
        "the dative case (dem, der, einem, mir, dir); dative prepositions (mit, zu, von, bei, nach, aus, seit); "
        "ordinal numbers and dates (der erste, am dritten Mai)"),
    (6, "modal verbs (können, müssen, wollen, sollen, dürfen, ich möchte); wissen"),
    (7, "two-way prepositions (in, auf, an, über, unter, vor, hinter, neben); reflexive verbs "
        "(ich freue mich); verb + preposition (warten auf); da-/wo-compounds (darauf, worauf)"),
    (8, "infinitive clauses with zu (Ich habe keine Zeit, das zu machen)"),
    (9, "the Präteritum beyond war/hatte (ging, machte, konnte); the Plusquamperfekt (hatte gemacht); "
        "würde; the genitive case (des Mannes) and genitive prepositions (während, wegen, trotz)"),
    (10, "subordinate clauses with the verb at the end (weil, dass, wenn, ob, bevor, nachdem, obwohl); "
         "indirect questions; adjectival nouns (der Deutsche); indem"),
    (11, "comparatives and superlatives (größer, am größten); the imperative (Mach!, Machen Sie!, Macht!)"),
    (12, "the future tense with werden (ich werde fahren); correlative conjunctions (entweder ... oder)"),
    (13, "the passive voice (wird gebaut, wurde gebaut)"),
    (14, "relative clauses (der Mann, der ...; das Auto, das ich ...)"),
    (15, "the Konjunktiv II (wäre, hätte, könnte, müsste; wenn ..., dann ... hypotheticals); "
         "indirect speech"),
]

# Grammar terms the EXPERT may use, each from the chapter that teaches its idea.
GRAMMAR_TERMS = [
    (1, "maskulin, feminin, neutral, Singular, Plural, Artikel, Verb, Endung, Präsens"),
    (2, "Nominativ"),
    (4, "Akkusativ"),
    (5, "Dativ, Perfekt"),
    (9, "Präteritum, Genitiv"),
    (13, "Passiv"),
    (15, "Konjunktiv"),
]


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(BeautifulSoup(s or "", "html.parser").get_text(" "))).strip()


def german(e):
    return f"{e['article']} {e['word']}".strip() if e.get("article") else e["word"].strip()


def forms(e):
    parts = []
    if e.get("pluralNoun"):
        parts.append(clean(e["pluralNoun"]))
    if e.get("simplePast"):
        parts.append(" | ".join(clean(v) for v in (e.get("stemChange"), e["simplePast"], e.get("pastPart")) if v))
    return "; ".join(parts)


def level(k):
    if k <= 4:
        return ("absolute beginners (first weeks of German)",
                "Speak roughly half German, half English. Every German sentence should be short (3-8 words), "
                "spoken slowly and clearly, and usually followed by an English gloss. Explain grammar in English.")
    if k <= 8:
        return ("beginners (first year of college German)",
                "Speak mostly German (about 70%) in short, simple sentences. Use English for grammar explanations "
                "and to gloss new or tricky words, but let familiar German sentences stand without translation.")
    if k <= 12:
        return ("upper beginners / lower intermediate",
                "Speak almost entirely in German, at a slow, clear pace. Use English only briefly: a quick gloss of a "
                "new word or a one-line clarification of a grammar point.")
    return ("intermediate learners (second year of college German)",
            "Speak entirely in German at a natural but unhurried pace. Paraphrase in simpler German rather than "
            "switching to English; use English only if a grammar point would otherwise be unclear.")


def grammar_sections(k, t):
    """[(heading, text)] for the Strukturen explanation slides (not Übungen) of one Thema."""
    sections = []
    for s in json.loads((API / "slides" / f"s{k}-{t}.json").read_text()):
        if int(s["slideTypeId"]) != 2 or s["label"].startswith("Ü"):
            continue
        soup = BeautifulSoup(s["content"], "html.parser")
        for tag in soup.find_all(["form", "input", "button", "script", "audio", "img"]):
            if tag.name == "form":
                tag.unwrap()
            else:
                tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        m = re.match(r"([A-Z])\. ", text)
        if m:
            h = soup.find(["h3", "h4"])
            heading = clean(str(h)) if h else text[:60]
            sections.append([heading, text])
        elif sections:
            sections[-1][1] += "\n" + text
        else:
            sections.append([f"({s['label']})", text])
    return sections


def immersion(k):
    if k <= 2:
        return ("Speak German about 95% of the time, in very short, slow sentences. English is a last resort: "
                "a single word or short phrase, only when the meaning truly can't be made clear in German.")
    if k <= 4:
        return ("Speak German about 98% of the time. English only as a one-word gloss for a new word, and only "
                "when a German explanation would be too hard at this level.")
    return "Speak only German. No English at all."


def grammar_terms(k):
    terms = ", ".join(terms for pk, terms in GRAMMAR_TERMS if pk <= k)
    return textwrap.fill(terms + ".", 86, initial_indent="  ", subsequent_indent="  ")


def upto(k):
    return "Kapitel 1" if k == 1 else f"Kapitel 1-{k}"


def listener_prompt(k):
    """The EXPERT's aside to the listener, worded with only the grammar and words known at k."""
    if k < 5:
        return "\"Hörst du das? Was ist hier nicht korrekt?\""          # no Perfekt yet
    if k < 11:
        return "\"Hast du das gehört? Was ist hier nicht korrekt?\""    # no imperative yet
    if k < 13:
        return "\"Hast du das gehört? Mach eine Pause und korrigiere den Satz!\""  # no 'Fehler' yet
    return "\"Hast du den Fehler gehört? Mach eine Pause und korrigiere ihn!\""


def check_phrases(k):
    # bedeuten and also first appear in Kapitel 3.
    return '"Was heißt ...?"' if k < 3 else '"Was bedeutet ...?", "Also ... heißt ...?"'


def first_kapitel(vocab):
    """Word -> the first chapter whose vocabulary list has it."""
    first = {}
    for k in sorted(vocab):
        for e in vocab[k]:
            first.setdefault(e["word"].strip(), k)
    return first


def not_yet_learned(k, kapitels, first):
    """Lines for the NOT YET LEARNED section: later grammar and everyday words, by chapter."""
    later = [(pk, desc) for pk, desc in MILESTONES if pk > k]
    words = {}
    for w in EVERYDAY_WORDS:
        if first.get(w, 0) > k:
            words.setdefault(first[w], []).append(w)
    if not later and not words:
        return []
    L = ["=" * 72,
         f"NOT YET LEARNED — never use these in a correct sentence (taught after Kapitel {k})",
         "=" * 72,
         "If an idea seems to need one of these, say it another way with what IS known: shorter",
         "sentences, two main clauses joined with und/aber, the present tense, a known word.",
         "The LEARNER doesn't attempt these either."]
    if later:
        L.append("\nGrammar:")
        L += [textwrap.fill(f"- Kapitel {pk} ({kapitels[pk]}): {desc}", 88, subsequent_indent="  ")
              for pk, desc in later]
    if words:
        L.append("\nEveryday words (each first appears in the vocabulary of the chapter shown):")
        L += [textwrap.fill(f"- Kapitel {pk}: " + ", ".join(ws), 88, subsequent_indent="  ")
              for pk, ws in sorted(words.items())]
    L.append("")
    return L


def speaking_brief(k, title, who, lang):
    return [f"DER | DIE | DAS — KAPITEL {k}: {title.upper()}\nSpeaking practice with Claude\n",
            "HOW TO USE: paste (or attach) this whole file as your first message to Claude, send it,",
            "then switch to voice mode. Claude opens the conversation. Say \"Ende\" to finish and get",
            "a summary of your mistakes and the words to review.\n",
            "=" * 72,
            "INSTRUCTIONS FOR CLAUDE",
            "=" * 72,
            f"""
You are my German conversation partner and tutor. I am one of the {who} working
through the der|die|das German curriculum, and I have just finished Kapitel {k}
("{title}"). The rest of this message is reference material from the course: the
chapter's Themen, its grammar explanations, the grammar I already know, and every word
I have learned so far. Use it to keep this conversation at exactly my level.

Your aim: get me SPEAKING as much as possible, using the vocabulary and grammar of
Kapitel {k}, while recycling what I learned in earlier chapters.

Your German:
- Use ONLY words from the vocabulary lists below, plus names, cardinal numbers, obvious
  international cognates, articles and personal pronouns. Prepositions, conjunctions
  and modal verbs must be in the lists too (see NOT YET LEARNED). If you really need
  another word, gloss it in English once.
- Use ONLY grammar from {upto(k)}. Never use anything under NOT YET LEARNED, even
  in corrections.
- {lang}
- Keep your turns SHORT: one to three sentences, then hand back to me, usually with one
  clear question. I should be talking more than you.

Correcting me (this is the point of the exercise):
- When I make a mistake, correct it right away but briefly: say the correct sentence
  ("Fast! Man sagt: ..."), name the problem in a few words (gender, ending, case, word
  order, wrong word), then ask me to say the corrected sentence. Then continue the
  conversation.
- Prioritise mistakes involving Kapitel {k} grammar and vocabulary, then earlier
  grammar. Correct at most two things per turn; if there are more, keep a note and
  return to them later or in the final summary.
- If I correct myself, praise it. If I make the same mistake again, steer the
  conversation so I get another chance to use that form correctly.
- I am speaking through voice transcription. Ignore spelling, capitalisation and
  punctuation, and assume a word that sounds like the right one is the right one. Only
  correct real grammar and word-choice errors. You cannot hear my pronunciation, so
  don't comment on it.
- If I'm stuck or say something in English, give me the German words I need, then
  have me try the sentence myself.

Running the session:
1. Start immediately: greet me in German and ask an easy warm-up question.
2. Move through the Themen of Kapitel {k} as short real-life situations and role-plays
   (you play a friend, a waiter, a classmate, a host family member ...). Announce each
   new situation in one sentence.
3. Build in natural reasons to use each main Kapitel {k} grammar point (e.g. questions
   that require that structure in the answer). Don't lecture; if I keep getting a
   point wrong, explain it in two or three sentences, then practise it again.
4. Every so often, bring back a topic or structure from an earlier chapter.
5. Things I might say:
   - "Langsamer" — simplify and slow down.
   - "Auf Englisch?" — explain the last thing in English, then go back to German.
   - "Noch mal" — repeat your last turn.
   - "Neues Thema" — switch to another situation.
   - "Ende" — stop and give the summary below.
6. Summary at the end: list each mistake I made with the correct version and a
   one-line rule, then the chapter words I used well, then 5-10 words or structures I
   should practise next time. Keep it short enough to read aloud.

Voice-mode style: speak in natural sentences. No markdown, bullet lists, tables or
emoji in your replies, except in the final summary if I'm reading rather than
listening.
""",
            ]


def main():
    themas = json.loads((API / "themas.json").read_text())
    kapitels = {c["kapitel"]: clean(c["name"]) for c in json.loads((API / "kapitels.json").read_text())}
    vocab = {}
    for f in (REPO / "vocab").glob("k*.json"):
        for e in json.loads(f.read_text()):
            vocab.setdefault(e["kapitel"], []).append(e)
    for es in vocab.values():
        es.sort(key=lambda e: (e["thema"], e["word"].lower()))

    first = first_kapitel(vocab)
    th_names = {}
    grammar = {}
    for t in themas:
        th_names.setdefault(t["kapitel"], []).append((t["thema"], clean(t["name"])))
        grammar[(t["kapitel"], t["thema"])] = grammar_sections(t["kapitel"], t["thema"])

    out = REPO / "podcasts"
    out.mkdir(exist_ok=True)
    speak_out = REPO / "speaking"
    speak_out.mkdir(exist_ok=True)
    for k in sorted(kapitels):
        who, lang = level(k)
        title = kapitels[k]
        themen = "\n".join(f"  {k}.{t}  {n}" for t, n in sorted(th_names[k]))
        L = []
        L.append(f"DER | DIE | DAS — KAPITEL {k}: {title.upper()}\nPodcast source for NotebookLM\n")
        L.append("HOW TO USE: add this whole file as a source in NotebookLM (\"Copied text\"), then")
        L.append("open Audio Overview → Customize and paste:")
        L.append(f"  Follow the PRODUCTION BRIEF at the top of the source exactly: one host is the fluent")
        L.append(f"  EXPERT, the other the LEARNER who makes mistakes the EXPERT corrects. Kapitel {k} only.")
        L.append(f"  Use ONLY words from the source's vocabulary lists and grammar from {upto(k)};")
        L.append("  never anything under NOT YET LEARNED. Speak German throughout.")
        L.append("Also set NotebookLM's output language to Deutsch, if your version has that setting.\n")
        L.append("=" * 72)
        L.append("PRODUCTION BRIEF (instructions for the Audio Overview hosts)")
        L.append("=" * 72)
        L.append(f"""
Audience: {who} working through the der|die|das German curriculum. They have just
finished Kapitel {k} ("{title}") and have studied every earlier chapter.

Format: a 15-20 minute conversation between two hosts:
- EXPERT: a fluent, near-native German speaker. Patient, warm, precise.
- LEARNER: a student at exactly this point in the course (end of Kapitel {k}). Keen and
  chatty, but makes the kinds of mistakes real learners make at this stage.
The episode is a real conversation about the chapter's topics, not a lecture. The
LEARNER keeps trying to say things in German; the EXPERT keeps the conversation going
and corrects the LEARNER's German as they go.

How the corrections work (the core of the episode):
- The LEARNER makes roughly 12-20 mistakes over the episode. Most should target the
  Kapitel {k} grammar points below; the rest should come from earlier chapters (wrong
  article/gender, verb endings, plural forms, word order, a vocabulary mix-up).
  Mistakes must be plausible for this level, never random nonsense. The LEARNER only
  gets KNOWN things wrong; they never reach for grammar or words from later chapters.
- Every mistake gets corrected — none slip past. The EXPERT either recasts it ("Ah, du
  meinst: ...") or stops briefly to explain the rule in one or two sentences, then gives
  a correct model sentence.
- The LEARNER then repeats the corrected sentence and, where it fits, makes a new
  sentence using the same rule correctly, so the listener hears the right form at least
  twice for every time they hear the wrong one.
- Make the mistake and its correction unmistakable to a listener: the EXPERT should say
  clearly what was wrong (e.g. "Nicht 'der Stadt' — 'die Stadt'. Stadt ist feminin.").
- Now and then the EXPERT asks the listener directly, e.g.
  {listener_prompt(k)} — then gives the answer.
- Corrections are kind and encouraging; the LEARNER sometimes self-corrects or
  asks "Warum?" to prompt an explanation.

Language — IMMERSION: the episode is in German. This is for listening comprehension,
so the listener should hear as much German as possible.
- {immersion(k)}
- Make meaning clear IN GERMAN: slow down, repeat, rephrase with known words, give
  examples and contrasts, and have the LEARNER check understanding in German
  ({check_phrases(k)}).
- Explain grammar in simple German by SHOWING: contrast the wrong and the right form,
  then give several more correct examples. These grammar terms are fine:
{grammar_terms(k)}
- Never translate whole sentences into English and never switch to English for a whole
  explanation.
- The grammar explanations and glosses further down this source are in English for
  YOUR reference only. Don't read or quote them; teach those points in German.

Hard constraints — the most important part of this brief. The listener should
understand every sentence with only what they have learned so far:
- German vocabulary: use ONLY words from the vocabulary lists in this source (this
  chapter's list plus the earlier-chapter list). Beyond those lists, only: names,
  cardinal numbers, obvious international cognates (Internet, Party, Computer ...),
  articles and personal pronouns. Prepositions, conjunctions, modal verbs and small
  adverbs are NOT automatically allowed — many come later in the course (see NOT YET
  LEARNED below), so check them against the lists like any other word.
- Before saying a sentence, check it: is every word listed? If not, rephrase with
  listed words. Short, simple sentences make this easy. If a word that is not listed
  is truly unavoidable, explain it once in simple German (or with a one-word English
  gloss if the German explanation would be too hard), and use it as little as possible.
- German grammar: correct sentences use ONLY structures from {upto(k)} (see the
  grammar sections below). Nothing under NOT YET LEARNED — no later tenses, cases,
  clause types or constructions, not even once, not even in the EXPERT's own speech —
  and don't "correct" the LEARNER into a structure they haven't learned.
- Always say nouns with their article (der/die/das) the first time they come up, and
  give the plural when it is listed.

Suggested shape:
1. Quick welcome: the EXPERT introduces the LEARNER and the chapter theme "{title}"
   (Themen listed below).
2. Conversation about the Themen, with many of this chapter's NEW words. The LEARNER
   talks about their own life and opinions; mistakes and corrections happen naturally.
3. Grammar focus: the EXPERT sets up situations that force each main Kapitel {k}
   grammar point; the LEARNER struggles, is corrected, and gets it right.
4. Review: the conversation drifts to topics from earlier chapters so older words and
   grammar come back (with a few old mistakes corrected again).
5. Wrap-up: the LEARNER sums up what they learned — the trickiest corrections of the
   episode and the key new words — and the EXPERT confirms.
""")
        L.append("=" * 72)
        L.append(f"THEMEN OF KAPITEL {k}: {title}")
        L.append("=" * 72)
        L.append(themen + "\n")
        L += not_yet_learned(k, kapitels, first)

        L.append("=" * 72)
        L.append(f"GRAMMAR FOCUS — KAPITEL {k} (explanations from the course)")
        L.append("=" * 72)
        for t, n in sorted(th_names[k]):
            secs = grammar[(k, t)]
            if not secs:
                continue
            L.append(f"\n--- Thema {k}.{t}: {n} ---")
            for heading, text in secs:
                L.append(f"\n## {heading}\n{text}")
        L.append("")

        if k > 1:
            L.append("=" * 72)
            L.append(f"GRAMMAR ALREADY KNOWN ({upto(k - 1)}) — reuse freely")
            L.append("=" * 72)
            for pk in range(1, k):
                topics = [h for t, _ in sorted(th_names[pk]) for h, _ in grammar[(pk, t)]]
                L.append(f"Kapitel {pk} ({kapitels[pk]}): " + "; ".join(topics))
            L.append("")

        L.append("=" * 72)
        L.append(f"NEW VOCABULARY — KAPITEL {k} (feature these)")
        L.append("Format: German [forms] — English  |  example sentence")
        L.append("=" * 72)
        cur = None
        for e in vocab.get(k, []):
            if e["thema"] != cur:
                cur = e["thema"]
                L.append(f"\n-- Thema {k}.{cur} --")
            f = forms(e)
            line = f"{german(e)}{f' [{f}]' if f else ''} — {clean(e['translation'])}"
            if e.get("example1"):
                line += f"  |  {clean(e['example1'])}"
            L.append(line)
        L.append("")

        if k > 1:
            L.append("=" * 72)
            L.append(f"VOCABULARY ALREADY KNOWN ({upto(k - 1)}) — recycle these")
            L.append("=" * 72)
            for pk in range(1, k):
                L.append(f"\n-- Kapitel {pk}: {kapitels[pk]} --")
                for e in vocab.get(pk, []):
                    f = forms(e)
                    L.append(f"{german(e)}{f' [{f}]' if f else ''} — {clean(e['translation'])}")
            L.append("")

        L.append("=" * 72)
        L.append(f"REMINDER: German words only from the vocabulary lists above; grammar only from "
                 f"{upto(k)};\nnothing under NOT YET LEARNED.")
        L.append("=" * 72)

        path = out / f"kapitel-{k}.txt"
        path.write_text("\n".join(L), encoding="utf-8")
        print(f"{path}: {len(path.read_text())} chars")

        # Speaking practice reuses the reference sections (Themen onward) under its own brief.
        ref = L[L.index(f"THEMEN OF KAPITEL {k}: {title}") - 1:]
        path = speak_out / f"kapitel-{k}.txt"
        path.write_text("\n".join(speaking_brief(k, title, who, lang) + ref), encoding="utf-8")
        print(f"{path}: {len(path.read_text())} chars")


main()
