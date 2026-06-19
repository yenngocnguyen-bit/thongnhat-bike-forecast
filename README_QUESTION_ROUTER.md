# Question Router

A classification pipeline that routes questions into three categories using heuristics and Claude API.

## Categories

- **reading_comprehension**: Question comes with a passage to read
- **reasoning**: Math, logic, or multi-step inference required
- **general**: Factual knowledge question

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

### Local Execution

```bash
# Full run
python question_router.py

# First 20 questions only
python question_router.py --limit 20

# Heuristic only (no API calls)
python question_router.py --dry-run

# Custom input file
python question_router.py --input mydata.json
```

### GitHub Actions

Trigger the workflow from the **Actions** tab:

1. Go to **Actions** → **Run Question Router**
2. Click **Run workflow**
3. (Optional) Set parameters:
   - **limit**: Process only N questions
   - **dry_run**: Check `true` to skip API calls
   - **input_file**: Custom input file path

Results are saved to `question_routing_results.json` and uploaded as artifacts.

## How It Works

1. **Heuristic Pass**: Fast pattern-matching for Vietnamese/English passage markers
2. **LLM Fallback**: Sends unclassified questions to Claude Sonnet 4.6 for classification
3. **Normalization**: Maps raw LLM output to canonical labels
4. **Summary Report**: Outputs distribution chart and statistics

## Output Format

```json
[
  {
    "qid": "q001",
    "label": "reasoning",
    "source": "llm"
  },
  {
    "qid": "q002",
    "label": "reading_comprehension",
    "source": "heuristic"
  }
]
```

## Input Format

Expected JSON structure:
```json
[
  {
    "qid": "q001",
    "question": "What is 2 + 2?",
    "choices": ["3", "4", "5", "6"]
  }
]
```

## Customization

Edit `question_router.py` to:
- Change model: `MODEL = "claude-opus-4-1"` (line 26)
- Adjust rate limiting: `SLEEP_SEC = 0.5` (line 28)
- Add more passage markers: `PASSAGE_MARKERS` list (lines 33-41)
- Modify system prompt: `SYSTEM_PROMPT` (lines 43-57)

## Requirements

- Python 3.10+
- Anthropic API key with access to Claude models
- `requests` library for HTTP calls
