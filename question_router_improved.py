"""
Question Routing Pipeline (Improved Version)
Classifies each question in the dataset into one of three categories:
  - reading_comprehension : question comes with a passage to read
  - reasoning             : math, logic, or multi-step inference required
  - general               : factual knowledge question

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python question_router_improved.py                         # full run
  python question_router_improved.py --limit 20              # first 20 questions
  python question_router_improved.py --dry-run               # heuristic only, no API calls
  python question_router_improved.py --input mydata.json     # custom input file
"""

import argparse
import json
import os
import time
import sys
import requests
from collections import Counter
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = "/mnt/user-data/uploads/public-test_1780368312.json"
DEFAULT_OUTPUT = "question_routing_results.json"
API_URL        = "https://api.anthropic.com/v1/messages"
MODEL          = "claude-3-5-sonnet-20241022"  # Latest Claude Sonnet model
MAX_TOKENS     = 50                    # only a short label needed
SLEEP_SEC      = 0.3                   # pause between API calls (rate-limit friendly)
CATEGORIES     = {"reading_comprehension", "reasoning", "general"}

# Passage-start markers - Vietnamese & English heuristic pre-filter
PASSAGE_MARKERS = [
    "đoạn thông tin",
    "đoạn văn",
    "đọc đoạn",
    "dựa vào đoạn",
    "cho đoạn",
    "passage:",
    "read the following",
]

SYSTEM_PROMPT = """\
You are a question-type classifier. Given a multiple-choice question (and its answer choices), \
output EXACTLY one of these three labels - nothing else:

  reading_comprehension
  reasoning
  general

Definitions:
- reading_comprehension : the question is accompanied by a text passage and asks about \
content in that passage.
- reasoning             : the question requires mathematical calculation, logical deduction, \
or multi-step inference (no passage provided).
- general               : the question tests factual or world-knowledge that can be answered \
directly (no passage, no calculation needed).

Respond with the label only. No punctuation, no explanation."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def heuristic_label(question: str) -> Optional[str]:
    """Return 'reading_comprehension' if the question clearly starts with a passage;
    otherwise return None so the LLM handles it."""
    q_lower = question.lower().strip()
    for marker in PASSAGE_MARKERS:
        if q_lower.startswith(marker):
            return "reading_comprehension"
    return None


def format_for_api(item: dict) -> str:
    """Format question and choices for API call."""
    choices_text = "\n".join(
        f"  {chr(65 + i)}. {c}" for i, c in enumerate(item.get("choices", []))
    )
    return f"Question:\n{item['question']}\n\nChoices:\n{choices_text}"


def call_api(question_text: str, api_key: str) -> str:
    """Send one question to the Anthropic API; return the raw response text.
    
    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model":      MODEL,
        "max_tokens": MAX_TOKENS,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": question_text}],
    }
    
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip().lower()
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout("API request timed out after 30 seconds")
    except requests.exceptions.HTTPError as e:
        raise requests.exceptions.HTTPError(
            f"API returned status {e.response.status_code}: {e.response.text}"
        )


def normalise_label(raw: str) -> str:
    """Map the model's raw text output to one of the three canonical labels."""
    for cat in CATEGORIES:
        if cat in raw:
            return cat
    if "reading" in raw or "comprehension" in raw:
        return "reading_comprehension"
    if "reason" in raw or "math" in raw or "logic" in raw or "calculat" in raw:
        return "reasoning"
    if "general" in raw or "factual" in raw or "knowledge" in raw:
        return "general"
    return "unknown"


def validate_item(item: dict, item_index: int) -> Optional[str]:
    """Validate that item has required fields. Return error message if invalid."""
    if not isinstance(item, dict):
        return f"Item {item_index} is not a dictionary: {type(item)}"
    if "qid" not in item:
        return f"Item {item_index} missing 'qid' field"
    if "question" not in item:
        return f"Item {item_index} (qid={item.get('qid')}) missing 'question' field"
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Route questions into three categories.")
    p.add_argument("--input",   default=DEFAULT_INPUT,  help="Path to input JSON file")
    p.add_argument("--output",  default=DEFAULT_OUTPUT, help="Path to write results JSON")
    p.add_argument("--limit",   type=int, default=None, help="Only process first N questions")
    p.add_argument("--dry-run", action="store_true",    help="Skip API calls; heuristic only")
    return p.parse_args()


def main():
    args = parse_args()

    # ── API key ──────────────────────────────────────────────────────────────
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        sys.exit(
            "ERROR: ANTHROPIC_API_KEY environment variable is not set.\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'\n"
            "Or run with --dry-run to test the heuristic without the API."
        )

    # ── Load data ────────────────────────────────────────────────────────────
    try:
        with open(args.input, encoding="utf-8") as f:
            dataset = json.load(f)
    except FileNotFoundError:
        sys.exit(f"ERROR: Input file '{args.input}' not found.")
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: Invalid JSON in '{args.input}': {e}")
    except Exception as e:
        sys.exit(f"ERROR: Failed to read '{args.input}': {e}")

    if not isinstance(dataset, list):
        sys.exit("ERROR: Input JSON must be a list of question objects.")

    if args.limit:
        dataset = dataset[: args.limit]

    # ── Classify ──────────────────────────────────────────────────────────────
    results     = []
    api_calls   = 0
    heuristic_n = 0
    errors      = 0
    skipped     = 0

    print(f"Processing {len(dataset)} questions  (model={MODEL})...\n")

    for i, item in enumerate(dataset, 1):
        # Validate item structure
        error_msg = validate_item(item, i)
        if error_msg:
            print(f"  [SKIP] {error_msg}")
            skipped += 1
            continue

        qid      = item["qid"]
        question = item["question"]

        # 1. Fast heuristic
        label  = heuristic_label(question)
        source = "heuristic"

        # 2. LLM fallback
        if label is None:
            if args.dry_run:
                label  = "unclassified"
                source = "dry-run"
            else:
                try:
                    raw    = call_api(format_for_api(item), api_key)
                    label  = normalise_label(raw)
                    source = "llm"
                    api_calls += 1
                    time.sleep(SLEEP_SEC)
                except requests.exceptions.Timeout:
                    print(f"  [WARN] {qid}: API timeout (exceeded 30s)")
                    label  = "error"
                    source = "error"
                    errors += 1
                except requests.exceptions.HTTPError as e:
                    print(f"  [WARN] {qid}: {e}")
                    label  = "error"
                    source = "error"
                    errors += 1
                except Exception as exc:
                    print(f"  [WARN] {qid}: {type(exc).__name__}: {exc}")
                    label  = "error"
                    source = "error"
                    errors += 1
        else:
            heuristic_n += 1

        results.append({"qid": qid, "label": label, "source": source})

        if i % 50 == 0 or i == len(dataset):
            print(f"  [{i:>4}/{len(dataset)}]  {qid}  ->  {label}  ({source})")

    # ── Save ──────────────────────────────────────────────────────────────────
    output_path = Path(args.output)
    
    # Create backup if output file already exists
    if output_path.exists():
        backup_path = output_path.with_suffix(".backup.json")
        output_path.rename(backup_path)
        print(f"Previous results backed up to {backup_path}")

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        sys.exit(f"ERROR: Failed to write results to '{args.output}': {e}")

    # ── Summary ────────────────────────────────────────────────────────────────
    counts = Counter(r["label"] for r in results)
    
    print(f"\n{'-'*60}")
    print(f"  Total processed     : {len(results)}")
    print(f"  Skipped (invalid)   : {skipped}")
    print(f"  API calls made      : {api_calls}")
    print(f"  Heuristic hits      : {heuristic_n}")
    print(f"  Errors              : {errors}")
    print(f"\n  Label distribution:")
    
    if counts:
        max_count = max(counts.values())
        for lbl, cnt in sorted(counts.items()):
            bar = "*" * (cnt * 30 // max_count) if max_count > 0 else ""
            pct = 100 * cnt / len(results) if len(results) > 0 else 0
            print(f"    {lbl:<30} {cnt:>4}  ({pct:>5.1f}%)  {bar}")
    
    print(f"\n  Output -> {args.output}")
    print(f"{'-'*60}")


if __name__ == "__main__":
    main()
