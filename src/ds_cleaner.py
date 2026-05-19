import json
import re
import unicodedata
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
RAW_DIR     = ROOT / "data" / "raw_data" / "cets"
CLEANED_DIR = ROOT / "data" / "processed_data" / "cets"

# ----Boilerplate patterns to remove----
BOILERPLATE_PATTERNS = [
    # Safe harbour / forward looking statements
    r"(?i)financial results conference call\.?.{0,200}opening remarks",
    r"(?i)describing our financial performance.{0,200}fiscal year 20\d\d",
    r"(?i)comments made during today'?s? call.{0,100}non-gaap results",
    r"(?i)please refer to our press release today.{0,300}forward-looking statements",
    r"(?i)forward[\s-]looking statements?.{0,600}actual results",
    r"(?i)safe harbor.{0,300}securities act",
    r"(?i)this (transcript|call|presentation) (may|contains|is provided).{0,200}",
    r"(?i)actual results (may|could|might) differ.{0,300}",
    r"(?i)during (this|the) conference call.{0,400}risks",
    r"(?i)subject to certain risks.{0,300}",
    r"(?i)private securities litigation.{0,300}",
    r"(?i)we would refer you to.{0,200}",
    r"(?i)form 10-k.{0,200}sec filings.{0,200}",
    r"(?i)reconciliation of gaap.{0,300}",
    r"(?i)non-gaap measures.{0,200}facilitate understanding.{0,200}",
    r"(?i)please note that all growth comparisons.{0,200}",
    r"(?i)posted on the investor relations.{0,300}",

    # Operator instructions
    r"(?i)^(operator|moderator):?.{0,200}$",
    r"(?i)please (hold|stand by|welcome|press|dial).{0,100}",
    r"(?i)your (line|call) is (open|now open).{0,100}",
    r"(?i)ladies and gentlemen.{0,200}",
    r"(?i)thank you for (joining|standing by|participating).{0,100}",
    r"(?i)this concludes (today'?s?|our|the).{0,100}",
    r"(?i)you may now disconnect.{0,100}",
    r"(?i)to (enter|ask|submit) (a )?question.{0,200}",
    r"(?i)press star.{0,100}",
    r"(?i)touchtone phone.{0,100}",
    r"(?i)please limit your question.{0,100}",
    r"(?i)we will (now )?begin the question.{0,100}",
    r"(?i)we will pause momentarily.{0,100}",
    r"(?i)assemble our roster.{0,100}",
    r"(?i)next question (is |comes )?(from|today).{0,200}",
    r"(?i)please go ahead.{0,50}",
    r"(?i)thank you for your question.{0,50}",
    r"(?i)there are no additional questions.{0,100}",
    r"(?i)that concludes (the|today'?s?).{0,100}",
    r"(?i)pass the call back.{0,100}",
    r"(?i)one moment for our next question.{0,100}",
    r"(?i)that will come from the line of.{0,200}",
    r"(?i)please stand by.{0,100}",

    # Opening pleasantries
    r"(?i)good (morning|afternoon|evening)(,? (everyone|ladies|gentlemen|and welcome)).{0,100}",
    r"(?i)welcome to (the|our|today'?s?).{0,100}(earnings|conference|call|results).{0,100}",
    r"(?i)thank you,? (operator|everyone|all|matt|hala|brian|lynn|cherie|hawk|kirsten|ji).{0,100}",
    r"(?i)i('ll| will) now turn (the call|it) (back |over )?(to|over).{0,100}",
    r"(?i)joining (us|me) (today|on the call).{0,200}",
    r"(?i)i would like to turn the (call|conference).{0,100}",
    r"(?i)as a reminder.{0,200}(recorded|conference|call).{0,100}",
    r"(?i)at this time.{0,50}(listen.only|listen only).{0,100}",
    r"(?i)if you have any (further|additional) questions.{0,100}",
    r"(?i)feel free to (contact|reach out).{0,100}",
    r"(?i)have a (great|good) (day|evening|weekend).{0,50}",
    r"(?i)thanks.{0,20}everybody.{0,50}",
    r"(?i)congratulations on (the|your).{0,50}(quarter|results).{0,50}",
    r"(?i)the conference will begin shortly.{0,100}",
    r"(?i)to raise your hand during.{0,100}",
    r"(?i)broadcom currently plans to report.{0,200}",
    r"(?i)a public webcast.{0,200}",
    r"(?i)audio replay.{0,200}",
    r"(?i)investor section of.{0,200}website.{0,100}",
    r"(?i)automated prompt.{0,50}",
    r"(?i)^N/A$",
    r"(?i)conference call is being webcast.{0,200}",
    r"(?i)press release and financial tables.{0,200}",
    r"(?i)if you did not receive a copy.{0,200}",
]

# ----Low signal sentences to filter----
LOW_SIGNAL_PATTERNS = [
    r"(?i)^(thank you\.?|thanks\.?|great(,? thank you)?\.?|sure\.?|absolutely\.?)$",
    r"(?i)^(next question|moving on|turning to|let('s| us) (move|turn|go)).{0,60}$",
    r"(?i)^(slide|page|exhibit|table|figure) \d+.{0,60}$",
    r"(?i)\(inaudible\)|\[inaudible\]|\(crosstalk\)|\[crosstalk\]",
    r"(?i)\[laughter\]|\(laughter\)|\[applause\]",
]

# ----Step 1: Remove duplicate transcript content----
def deduplicate_transcript(text: str) -> str:
    # Skip past any short header noise to find a more unique fingerprint
    # Use a longer, more specific chunk from deeper in the text
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 100]

    if not lines:
        return text

    # Use the first substantial line as fingerprint
    fingerprint = lines[0][:150]

    # Look for it appearing a second time
    first = text.find(fingerprint)
    second = text.find(fingerprint, first + 100)

    if second != -1:
        print(f"  duplicate detected — truncating at position {second}")
        return text[:second].strip()

    return text

# ----Step 2: Normalise unicode----
def normalise_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text

# ----Step 3: Strip speaker labels (must run BEFORE fix_line_breaks)----
def strip_speaker_labels(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) < 60 and not line[-1] in ".?!,:;":
            if re.match(r"(?i)^[A-Z][a-zA-Z\s\.\-,]+$", line):
                continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

# ----Step 4: Fix mid-word line breaks (must run AFTER strip_speaker_labels)----
def fix_line_breaks(text: str) -> str:
    text = re.sub(r"(\w)\n(\w)", r"\1 \2", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text

# ----Step 5: Strip boilerplate blocks----
def strip_boilerplate(text: str) -> str:
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.MULTILINE)
    return text

# ----Step 6: Clean individual sentences----
def clean_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence)
    sentence = re.sub(r"\[.*?\]", "", sentence)
    sentence = re.sub(r"\(.*?inaudible.*?\)", "", sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"[^\x00-\x7F]+", "", sentence)
    return sentence.strip()

# ----Step 7: Filter low signal sentences----
def is_low_signal(sentence: str) -> bool:
    if len(sentence.split()) < 6:
        return True
    if len(sentence.split()) > 80:
        return True
    for pattern in LOW_SIGNAL_PATTERNS:
        if re.search(pattern, sentence):
            return True
    alpha_chars = sum(c.isalpha() for c in sentence)
    if len(sentence) > 0 and alpha_chars / len(sentence) < 0.4:
        return True
    return False

# ----Debug: check which patterns are matching----
def debug_patterns(text: str):
    print("\n--- BOILERPLATE PATTERN DEBUG ---")
    for pattern in BOILERPLATE_PATTERNS:
        matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if matches:
            print(f"  MATCHED ({len(matches)}x): {pattern[:60]}")
        else:
            print(f"  no match: {pattern[:60]}")

    print("\n--- SHORT LINES KEPT ---")
    for line in text.split("\n"):
        line = line.strip()
        if 0 < len(line) < 60 and line[-1] not in ".?!,:;":
            print(f"  '{line}'")

# ----Master cleaning function----
def clean_transcript(raw_text: str, debug: bool = False) -> str:
    text = deduplicate_transcript(raw_text)  # 1. remove duplicates
    text = normalise_unicode(text)           # 2. fix encoding
    text = strip_speaker_labels(text)        # 3. remove labels while on own lines
    text = fix_line_breaks(text)             # 4. join broken lines after labels gone
    text = strip_boilerplate(text)           # 5. remove boilerplate

    if debug:
        debug_patterns(text)

    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned = []
    for sentence in sentences:
        sentence = clean_sentence(sentence)
        if sentence and not is_low_signal(sentence):
            cleaned.append(sentence)

    return " ".join(cleaned)

# ----Process all raw CET files----
def clean_all(debug_first: bool = True):
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    files = list(RAW_DIR.glob("*.json"))
    print(f"Found {len(files)} raw transcripts to clean")

    for i, path in enumerate(files):
        out_path = CLEANED_DIR / path.name

        if out_path.exists():
            print(f"  skipping — already cleaned: {path.name}")
            continue

        with open(path) as f:
            raw = json.load(f)

        run_debug = debug_first and i == 0
        cleaned_text = clean_transcript(raw["transcript"], debug=run_debug)

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

        raw_len     = len(raw["transcript"].split())
        cleaned_len = len(cleaned_text.split())
        ratio       = round((1 - cleaned_len / raw_len) * 100, 1)
        print(f"  cleaned: {path.name} | {raw_len} → {cleaned_len} words ({ratio}% removed)")

    print(f"\nDone. Cleaned transcripts saved to {CLEANED_DIR}")

clean_all()