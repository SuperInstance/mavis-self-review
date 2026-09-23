"""Test runner for mavis-self-review."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/workspace/repos/mavis-self-review")

from mavis_self_review.canary import canary
from mavis_self_review.reviewer import (
    extract_todos, extract_finished, extract_facts, extract_doctrine_anchors,
    parse_memory_entry, review_productivity, identify_gaps, suggest_improvements,
    full_review,
)

results = []
failures = []


def test(name, func):
    try:
        func()
        results.append((name, "PASS"))
    except AssertionError as e:
        results.append((name, f"FAIL: {e}"))
        failures.append(name)
    except Exception as e:
        results.append((name, f"ERROR: {type(e).__name__}: {e}"))
        failures.append(name)


def t_canary():
    assert canary() == "0x24a555471370b18d"


def t_extract_finished():
    text = "- [x] ship the book\n- [done] push repo\n"
    f = extract_finished(text)
    assert len(f) >= 1


def t_extract_todos():
    text = "Next: build the conductor. TODO: harden the witness."
    t = extract_todos(text)
    assert any("conductor" in x for x in t)
    assert any("witness" in x for x in t)


def t_extract_facts():
    text = "5 tools built. 12 tests passing."
    facts = extract_facts(text)
    assert any("5" in x and "tools" in x for x in facts)


def t_extract_doctrine():
    text = "`cells_are_scars` `witness_log_is_prediction`"
    d = extract_doctrine_anchors(text)
    assert "cells_are_scars" in d
    assert "witness_log_is_prediction" in d


def t_parse_memory():
    text = """### Sept 23 — Tools shipped — 2026-09-23

## Built

5 tools.

## Verified

8 tests pass.
"""
    entry = parse_memory_entry(text)
    assert entry["title"] is not None
    assert "Built" in entry["sections"]


def t_review_productivity_empty():
    r = review_productivity({})
    assert r["items_shipped"] == 0
    assert r["files_analyzed"] == 0


def t_review_productivity_with_data():
    files = {
        Path("a.md"): "- [x] done\n**Next**: more work",
        Path("b.md"): "- [x] also done",
    }
    r = review_productivity(files)
    assert r["files_analyzed"] == 2
    assert r["items_shipped"] == 2
    assert r["items_pending"] >= 1


def t_identify_gaps():
    """Test gap detection in fake repo."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "myrepo"
        repo.mkdir()
        (repo / "main.py").write_text("# TODO: this needs work\nprint('hi')\n# FIXME: bug\n")
        gaps = identify_gaps([repo])
        assert len(gaps) >= 1


def t_suggest_improvements_high_rate():
    review = {
        "items_shipped": 10,
        "items_pending": 2,
        "shipping_rate": 83,
        "doctrines_seen": ["a", "b", "c", "d", "e"],
    }
    suggestions = suggest_improvements(review, [])
    assert any(s["priority"] == "maintain" for s in suggestions)


def t_suggest_improvements_low_rate():
    review = {
        "items_shipped": 2,
        "items_pending": 10,
        "shipping_rate": 17,
        "doctrines_seen": [],
    }
    suggestions = suggest_improvements(review, [])
    assert any(s["priority"] == "high" for s in suggestions)


def t_full_review():
    """Integration test."""
    with tempfile.TemporaryDirectory() as td:
        mem_dir = Path(td) / "mem"
        mem_dir.mkdir()
        (mem_dir / "a.md").write_text("- [x] shipped tool\n Next: more\n Doctrine: `cells_are_scars`")

        repos_dir = Path(td) / "repos"
        repos_dir.mkdir()

        result = full_review(mem_dir, repos_dir)
        assert "productivity" in result
        assert "code_gaps" in result
        assert "suggestions" in result


test("test_canary", t_canary)
test("test_extract_finished", t_extract_finished)
test("test_extract_todos", t_extract_todos)
test("test_extract_facts", t_extract_facts)
test("test_extract_doctrine", t_extract_doctrine)
test("test_parse_memory", t_parse_memory)
test("test_review_productivity_empty", t_review_productivity_empty)
test("test_review_productivity_with_data", t_review_productivity_with_data)
test("test_identify_gaps", t_identify_gaps)
test("test_suggest_improvements_high_rate", t_suggest_improvements_high_rate)
test("test_suggest_improvements_low_rate", t_suggest_improvements_low_rate)
test("test_full_review", t_full_review)

print("\n=== mavis-self-review test results ===")
for name, status in results:
    print(f"  {status:60} {name}")

print(f"\n{len(results) - len(failures)}/{len(results)} passed")
if failures:
    sys.exit(1)
