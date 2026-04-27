import json
import re
import unicodedata
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
RAW_DIR     = ROOT / "data" / "raw_data" / "cets"
CLEANED_DIR = ROOT / "data" / "processed_data" / "cets"
print(f"ROOT: {ROOT}")
print(f"RAW_DIR: {RAW_DIR}")
print(f"CLEANED_DIR: {CLEANED_DIR}")
print(f"Files found: {list(RAW_DIR.glob('*.json'))}")

# ----Boilerplate patterns to remove----
BOILERPLATE_PATTERNS = [
    # Safe harbour / forward looking statements
    r"(?i)forward[\s-]looking statements?.{0,600}actual results",
    r"(?i)safe harbor.{0,300}securities act",
    r"(?i)this (transcript|call|presentation) (may|contains|is provided).{0,200}",
    r"(?i)actual results (may|could|might) differ.{0,300}",

    # Operator instructions
    r"(?i)^(operator|moderator):?.{0,200}$",
    r"(?i)please (hold|stand by|welcome|press|dial).{0,100}",
    r"(?i)your (line|call) is (open|now open).{0,100}",
    r"(?i)ladies and gentlemen.{0,200}",
    r"(?i)thank you for (joining|standing by|participating).{0,100}",
    r"(?i)this concludes (today'?s?|our|the).{0,100}",
    r"(?i)you may now disconnect.{0,100}",

    # Opening pleasantries
    r"(?i)good (morning|afternoon|evening)(,? (everyone|ladies|gentlemen|and welcome)).{0,100}",
    r"(?i)welcome to (the|our).{0,100}(earnings|conference|call|results).{0,100}",
    r"(?i)thank you,? (operator|everyone|all).{0,100}",
    r"(?i)i('ll| will) now turn (the call|it) (back |over )?(to|over).{0,100}",
    r"(?i)joining (us|me) (today|on the call).{0,200}",
]

# ----Low signal sentences to filter----
LOW_SIGNAL_PATTERNS = [
    r"(?i)^(thank you\.?|thanks\.?|great(,? thank you)?\.?|sure\.?|absolutely\.?)$",
    r"(?i)^(next question|moving on|turning to|let('s| us) (move|turn|go)).{0,60}$",
    r"(?i)^(slide|page|exhibit|table|figure) \d+.{0,60}$",
    r"(?i)\(inaudible\)|\[inaudible\]|\(crosstalk\)|\[crosstalk\]",
    r"(?i)\[laughter\]|\(laughter\)|\[applause\]",
]

# ----Layer 1: Normalise unicode----
def normalise_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text

# ----Layer 2: Strip speaker labels----
def strip_speaker_labels(text: str) -> str:
    """
    Speaker names and designations sit on their own lines.
    They follow the pattern of short lines (under 60 chars)
    that don't end in punctuation — i.e. not a sentence.
    """
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip short lines with no sentence-ending punctuation
        # that look like names or titles
        if len(line) < 60 and not line[-1] in ".?!,:;":
            # Extra check — if it looks like a name/title skip it
            if re.match(r"(?i)^[A-Z][a-zA-Z\s\.\-,]+$", line):
                continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

# ----Layer 3: Strip boilerplate blocks----
def strip_boilerplate(text: str) -> str:
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.MULTILINE)
    return text

# ----Layer 4: Clean individual sentences----
def clean_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence)          # collapse whitespace
    sentence = re.sub(r"\[.*?\]", "", sentence)        # remove [annotations]
    sentence = re.sub(r"\(.*?inaudible.*?\)", "", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"[^\x00-\x7F]+", "", sentence) # remove non-ascii
    return sentence.strip()

# ----Layer 5: Filter low signal sentences----
def is_low_signal(sentence: str) -> bool:
    # Too short
    if len(sentence.split()) < 6:
        return True
    # Too long — likely compound legal sentence
    if len(sentence.split()) > 80:
        return True
    # Matches low signal patterns
    for pattern in LOW_SIGNAL_PATTERNS:
        if re.search(pattern, sentence):
            return True
    # Mostly numbers and symbols
    alpha_chars = sum(c.isalpha() for c in sentence)
    if len(sentence) > 0 and alpha_chars / len(sentence) < 0.4:
        return True
    return False

# ----Master cleaning function----
def clean_transcript(raw_text: str) -> str:
    # Apply layers in order
    text = normalise_unicode(raw_text)
    text = strip_speaker_labels(text)
    text = strip_boilerplate(text)

    # Split into sentences and clean each one
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned = []
    for sentence in sentences:
        sentence = clean_sentence(sentence)
        if sentence and not is_low_signal(sentence):
            cleaned.append(sentence)

    return " ".join(cleaned)

# ----Process all raw CET files----
def clean_all():
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    files = list(RAW_DIR.glob("*.json"))
    print(f"Found {len(files)} raw transcripts to clean")

    for path in files:
        out_path = CLEANED_DIR / path.name

        if out_path.exists():
            print(f"  skipping — already cleaned: {path.name}")
            continue

        with open(path) as f:
            raw = json.load(f)

        cleaned_text = clean_transcript(raw["transcript"])

        output = {
            "ticker":     raw["ticker"],
            "date":       raw["date"],
            "quarter":    raw.get("quarter", ""),
            "year":       raw.get("year", ""),
            "source_url": raw["source_url"],
            "transcript": cleaned_text,
        }

        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)

        # Show compression ratio so you can see how much was removed
        raw_len     = len(raw["transcript"].split())
        cleaned_len = len(cleaned_text.split())
        ratio       = round((1 - cleaned_len / raw_len) * 100, 1)
        print(f"  cleaned: {path.name} | {raw_len} → {cleaned_len} words ({ratio}% removed)")

    print(f"\nDone. Cleaned transcripts saved to {CLEANED_DIR}")

clean_all()