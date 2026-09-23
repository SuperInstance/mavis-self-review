"""CLI for mavis-self-review."""
import argparse
import json
import sys
from pathlib import Path

from .reviewer import (
    parse_memory_entry,
    extract_todos,
    extract_finished,
    extract_facts,
    extract_doctrine_anchors,
    review_productivity,
    identify_gaps,
    suggest_improvements,
    full_review,
)


def cmd_review(args):
    """Full self-review."""
    memory_dir = Path(args.memory_dir) if args.memory_dir else None
    repos_dir = Path(args.repos_dir) if args.repos_dir else Path("/workspace/repos")

    result = full_review(memory_dir, repos_dir)
    if args.json:
        print(json.dumps(result, indent=1, default=str))
        return

    p = result["productivity"]
    print(f"=== Self-Review ===")
    print(f"Files analyzed: {p['files_analyzed']}")
    print(f"Items shipped: {p['items_shipped']}")
    print(f"Items pending: {p['items_pending']}")
    print(f"Shipping rate: {p['shipping_rate']:.1f}%")
    print(f"Doctrines referenced: {len(p['doctrines_seen'])}")
    print(f"Facts extracted: {p['fact_count']}")
    print()
    print(f"Code TODOs/FIXMEs: {len(result['code_gaps'])}")
    print()
    print("=== Suggestions ===")
    for s in result["suggestions"]:
        print(f"  [{s['priority'].upper()}] {s['name']}: {s['rationale']}")


def cmd_gaps(args):
    """Just show code gaps."""
    repos_dir = Path(args.repos_dir) if args.repos_dir else Path("/workspace/repos")
    repo_dirs = [d for d in repos_dir.iterdir() if d.is_dir() and d.name.startswith(("quilt-canon-", "mavis-", "quilt-fleet-"))]
    gaps = identify_gaps(repo_dirs)
    for g in gaps:
        print(f"  {g['repo']}/{g['file']}: {g['comment']}")


def cmd_suggestions(args):
    """Just show improvement suggestions."""
    memory_dir = Path(args.memory_dir) if args.memory_dir else None
    repos_dir = Path(args.repos_dir) if args.repos_dir else Path("/workspace/repos")
    result = full_review(memory_dir, repos_dir)
    for s in result["suggestions"]:
        print(f"  [{s['priority'].upper()}] {s['name']}: {s['rationale']}")


def main():
    p = argparse.ArgumentParser(description="mavis-self-review — analyze past work, find gaps, suggest improvements")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_r = sub.add_parser("review", help="Full self-review")
    p_r.add_argument("--memory-dir")
    p_r.add_argument("--repos-dir")
    p_r.add_argument("--json", action="store_true")
    p_r.set_defaults(func=cmd_review)

    sub.add_parser("gaps", help="Show code-level gaps (TODO/FIXME)").set_defaults(func=cmd_gaps)
    p_g = sub.add_parser("gaps", help="Show code-level gaps")
    p_g.add_argument("--repos-dir")
    p_g.set_defaults(func=cmd_gaps)

    sub.add_parser("suggestions", help="Show improvement suggestions").set_defaults(func=cmd_suggestions)
    p_s = sub.add_parser("suggestions", help="Show improvement suggestions")
    p_s.add_argument("--memory-dir")
    p_s.add_argument("--repos-dir")
    p_s.set_defaults(func=cmd_suggestions)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
