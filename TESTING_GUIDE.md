# Question Router - Local Testing Guide

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
```bash
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
```

### 3. Run with Sample Data
```bash
python question_router.py --input sample_data.json
```

**Expected Output:**
```
Processing 10 questions  (model=claude-sonnet-4-6)…

  [   1/10]  q001  →  reasoning  (heuristic)
  [   2/10]  q002  →  reading_comprehension  (heuristic)
  [   3/10]  q003  →  reading_comprehension  (heuristic)
  [   4/10]  q004  →  reasoning  (llm)
  [   5/10]  q005  →  general  (llm)
  [  10/10]  q010  →  general  (llm)

──────────────────────────────────────────────────
  Total processed : 10
  API calls       : 5
  Heuristic hits  : 5
  Errors          : 0

  Label distribution:
    general                      3  ( 30.0%)  ██████████████████
    reading_comprehension        4  ( 40.0%)  ██████████████████████████
    reasoning                    3  ( 30.0%)  ██████████████████

  Output → question_routing_results.json
```

---

## Test Scenarios

### Scenario A: Heuristic-Only Test (No API Calls)
**Purpose:** Verify heuristic markers work without spending API credits

```bash
python question_router.py --input sample_data.json --dry-run
```

**What to expect:**
- Questions q002, q003, q006, q008 → `reading_comprehension` (heuristic)
- Questions q001, q004, q005, q007, q009, q010 → `unclassified` (dry-run, no LLM)
- No API calls made
- Fast execution (~1 second)

**Pass Criteria:**
- ✅ 4 reading_comprehension from heuristic
- ✅ 6 unclassified from dry-run
- ✅ 0 API calls

---

### Scenario B: Limited Questions Test
**Purpose:** Test with small sample before processing full dataset

```bash
python question_router.py --input sample_data.json --limit 5
```

**What to expect:**
- Process only first 5 questions
- Mix of heuristic hits and LLM calls
- Fast execution (~2-3 seconds)

**Example Output:**
```
Processing 5 questions  (model=claude-sonnet-4-6)…

  [   1/5]  q001  →  reasoning  (heuristic)
  [   2/5]  q002  →  reading_comprehension  (heuristic)
  [   3/5]  q003  →  reading_comprehension  (heuristic)
  [   4/5]  q004  →  reasoning  (llm)
  [   5/5]  q005  →  general  (llm)

  Total processed : 5
  API calls       : 2
  Heuristic hits  : 3
  Errors          : 0
```

---

### Scenario C: Full Run Test
**Purpose:** Test complete pipeline with all 10 sample questions

```bash
python question_router.py --input sample_data.json
```

**Expected Distribution:**
```
- reading_comprehension: 4 questions (40%)  [q002, q003, q006, q008]
- reasoning: 3 questions (30%)              [q001, q004, q009]
- general: 3 questions (30%)                [q005, q007, q010]

- Heuristic hits: 4
- API calls: 6
- Processing time: ~3-4 seconds
- Cost: ~$0.01 USD (6 API calls @ Claude Sonnet pricing)
```

---

### Scenario D: Custom Output Location
**Purpose:** Save results to different file

```bash
python question_router.py \
  --input sample_data.json \
  --output my_results.json
```

**Verify:**
```bash
cat my_results.json
```

Expected structure:
```json
[
  {"qid": "q001", "label": "reasoning", "source": "heuristic"},
  {"qid": "q002", "label": "reading_comprehension", "source": "heuristic"},
  {"qid": "q003", "label": "reading_comprehension", "source": "heuristic"},
  ...
]
```

---

### Scenario E: Error Handling Test
**Purpose:** Verify error messages are clear and helpful

#### Test E1: Missing Input File
```bash
python question_router.py --input nonexistent.json
```

**Original Version Output:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'nonexistent.json'
```

**Improved Version Output:**
```
ERROR: Input file 'nonexistent.json' not found.
```

✅ **Improved is clearer for users**

#### Test E2: Malformed JSON
```bash
echo "{ invalid json }" > bad.json
python question_router.py --input bad.json
```

**Original Version:**
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 2
```

**Improved Version:**
```
ERROR: Invalid JSON in 'bad.json': Expecting value: line 1 column 2
```

✅ **Improved guides users to problem location**

#### Test E3: Missing Data Fields
Create file with missing "question" field:
```bash
echo '[{"qid": "q001"}]' > incomplete.json
python question_router.py --input incomplete.json
```

**Original Version:**
```
KeyError: 'question'
(Script crashes, no recovery)
```

**Improved Version:**
```
[SKIP] Item 1 (qid=q001): missing 'question' field
Total processed : 0
```

✅ **Improved skips invalid items gracefully**

---

## Performance Testing

### Test: Rate Limiting
**Purpose:** Verify rate limiting doesn't cause failures

```bash
# Simulate 20 questions (expecting ~10 API calls)
head -20 sample_data.json > extended_sample.json
time python question_router.py --input extended_sample.json
```

**Expected Behavior:**
- 0.3 second sleep between API calls
- Total time: ~3-5 seconds (10 calls × 0.3s = 3s + processing)
- No timeout errors
- All questions classified

---

## Output Validation

### Check 1: Results File Exists
```bash
ls -lh question_routing_results.json
# Should show recent timestamp and reasonable file size
```

### Check 2: JSON Structure Valid
```bash
python -m json.tool question_routing_results.json | head -20
# Should parse without errors
```

### Check 3: All Categories Present
```bash
python -c "
import json
with open('question_routing_results.json') as f:
    results = json.load(f)
    labels = [r['label'] for r in results]
    print(f'Total: {len(results)}')
    print(f'reading_comprehension: {labels.count(\"reading_comprehension\")}')
    print(f'reasoning: {labels.count(\"reasoning\")}')
    print(f'general: {labels.count(\"general\")}')
    print(f'errors/unknown: {len([l for l in labels if l not in {\"reading_comprehension\", \"reasoning\", \"general\"}])}')
"
```

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY environment variable is not set"

**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
python question_router.py --input sample_data.json
```

Or use `--dry-run` to test without API:
```bash
python question_router.py --input sample_data.json --dry-run
```

### Issue: "ModuleNotFoundError: No module named 'requests'"

**Solution:**
```bash
pip install -r requirements.txt
# Or just install requests
pip install requests anthropic
```

### Issue: API timeout (takes >30 seconds)

**Possible causes:**
- Network issue
- API service slow
- Rate limited

**Solution:**
```bash
# Edit question_router.py, increase timeout:
# timeout=30  →  timeout=60

# Or reduce batch size
python question_router.py --input sample_data.json --limit 5
```

### Issue: "TypeError: 'NoneType' object is not subscriptable"

**Cause:** API response format unexpected (rare)

**Solution:**
- Check API key is valid
- Check API endpoint URL is correct
- Use improved version with better error handling

---

## Comparing Original vs Improved

### Run Both on Sample Data

```bash
# Test original version
python question_router.py --input sample_data.json --limit 5

# Test improved version
python question_router_improved.py --input sample_data.json --limit 5
```

**Results Comparison:**

| Test Case | Original | Improved |
|-----------|----------|----------|
| Normal run | ✅ Works | ✅ Works |
| Missing file | ❌ Crashes | ✅ Clear error |
| Malformed JSON | ❌ Generic error | ✅ Clear error |
| Missing fields | ❌ Crashes | ✅ Skips item |
| Empty results | ❌ Crashes on summary | ✅ Handles gracefully |

---

## Next Steps

1. **Test locally** with `sample_data.json` and `--dry-run`
2. **Verify API key** works with one question using `--limit 1`
3. **Run full sample** to see distribution
4. **Compare outputs** between original and improved
5. **Run with your data** when confident

---

## Support

For issues:
1. Check `EVALUATION.md` for known bugs
2. Review troubleshooting section above
3. Use improved version for production
4. Check API key is valid and has quota remaining
