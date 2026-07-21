import json
import nltk
import torch
from pathlib import Path
from transformers import pipeline

# Download sentence tokenizer on first run
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
from nltk.tokenize import sent_tokenize

ROOT          = Path(__file__).resolve().parent.parent
CLEANED_DIR   = ROOT / "data" / "processed_data" / "cets"
SENTIMENT_DIR = ROOT / "data" / "processed_data" / "sentiment"

# ----Load FinBERT once at module level — expensive to reload per transcript----
print("Loading FinBERT...")
finbert = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    top_k=None,
    device=0 if torch.cuda.is_available() else -1
)
print("FinBERT loaded.")

def score_sentence(sentence: str) -> dict | None:
    """
    Score a single sentence with FinBERT.
    Returns dict with positive, negative, neutral scores.
    Returns None if sentence is too short to score meaningfully.
    """
    if len(sentence.split()) < 5:
        return None

    try:
        result = finbert(sentence[:512], truncation=True)
        scores = {item["label"]: item["score"] for item in result[0]}
        return {
            "positive": scores.get("positive", 0),
            "negative": scores.get("negative", 0),
            "neutral":  scores.get("neutral",  0),
        }
    except Exception as e:
        print(f"  scoring error: {e}")
        return None

def score_transcript(transcript_text: str) -> dict:
    """
    Split transcript into sentences, score each with FinBERT,
    and return aggregate sentiment scores.
    """
    sentences = sent_tokenize(transcript_text)

    pos_scores = []
    neg_scores = []
    neu_scores = []

    for sentence in sentences:
        result = score_sentence(sentence)
        if result is None:
            continue
        pos_scores.append(result["positive"])
        neg_scores.append(result["negative"])
        neu_scores.append(result["neutral"])

    if not pos_scores:
        return {
            "net_sentiment":    0.0,
            "avg_positive":     0.0,
            "avg_negative":     0.0,
            "avg_neutral":      0.0,
            "sentences_scored": 0,
        }

    avg_pos = sum(pos_scores) / len(pos_scores)
    avg_neg = sum(neg_scores) / len(neg_scores)
    avg_neu = sum(neu_scores) / len(neu_scores)

    return {
        "net_sentiment":    round(avg_pos - avg_neg, 6),
        "avg_positive":     round(avg_pos, 6),
        "avg_negative":     round(avg_neg, 6),
        "avg_neutral":      round(avg_neu, 6),
        "sentences_scored": len(pos_scores),
    }

def score_all():
    SENTIMENT_DIR.mkdir(parents=True, exist_ok=True)

    files = list(CLEANED_DIR.glob("*.json"))
    print(f"Found {len(files)} cleaned transcripts to score")

    for i, path in enumerate(files):
        out_path = SENTIMENT_DIR / path.name

        if out_path.exists():
            print(f"  skipping — already scored: {path.name}")
            continue

        with open(path) as f:
            cleaned = json.load(f)

        print(f"  scoring: {path.name}", end=" → ")

        scores = score_transcript(cleaned["transcript"])

        output = {
            "ticker":           cleaned["ticker"],
            "date":             cleaned["date"],
            "quarter":          cleaned.get("quarter", ""),
            "year":             cleaned.get("year", ""),
            "net_sentiment":    scores["net_sentiment"],
            "avg_positive":     scores["avg_positive"],
            "avg_negative":     scores["avg_negative"],
            "avg_neutral":      scores["avg_neutral"],
            "sentences_scored": scores["sentences_scored"],
        }

        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)

        print(
            f"net={scores['net_sentiment']:+.4f} | "
            f"pos={scores['avg_positive']:.3f} | "
            f"neg={scores['avg_negative']:.3f} | "
            f"sentences={scores['sentences_scored']}"
        )

    print(f"\nDone. Sentiment scores saved to {SENTIMENT_DIR}")


score_all()
