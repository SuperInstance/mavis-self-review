# mavis-self-review

Self-analysis tool for Mavis. Examines past memory + code for productivity, gaps, and improvement suggestions.

## Concept

The substrate walker learns by inspecting its own witness log. This tool:
- Parses memory entries for facts, todos, finished items, doctrines
- Identifies code TODO/FIXME comments
- Computes shipping rate (shipped vs pending)
- Suggests improvements based on patterns

## Run

```bash
python3 -m mavis_self_review review --memory-dir <dir> --repos-dir <dir>
python3 -m mavis_self_review gaps --repos-dir <dir>
python3 -m mavis_self_review suggestions --memory-dir <dir>
```

## Tests

```bash
python3 run_tests.py    # 12/12 passing
```

## Substrate

Reflective substrate — pattern analysis over memory and code.

## Connection

- `mavis-fleet-canary` — verifies canary across fleet
- `mavis-skill-miner` — proposes skills from patterns
- This: reviews past work → identifies improvements → drives next iteration
