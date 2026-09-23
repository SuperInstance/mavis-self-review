"""Self-review — analyzes Mavis's past work and finds improvement patterns.

What gets analyzed:
- Memory entries (work done across sessions)
- Canon pieces (prose quality)
- Commit history (repos built)
- Test results (pass/fail patterns)
- Error logs

What gets produced:
- Productivity summary (what got built)
- Failure patterns (where did things break)
- Gaps (what was attempted but not finished)
- Improvement suggestions (concrete next steps)
"""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re


def parse_memory_entry(text: str) -> Dict:
    """Parse a memory entry into structured fields."""
    entry = {
        "date": None,
        "title": None,
        "tags": [],
        "sections": {},
    }

    # Date
    date_match = re.search(r"### ([A-Z][a-z]+ \d+ — [^—]*?— \d{4}-\d{2}-\d{2})", text)
    if not date_match:
        date_match = re.search(r"### ([^\n]{10,80})", text)
    if date_match:
        entry["title"] = date_match.group(1).strip()

    # Markdown sections
    current = None
    for line in text.split("\n"):
        if line.startswith("## "):
            current = line.strip("# ").strip()
            entry["sections"][current] = []
        elif current:
            entry["sections"][current].append(line)

    return entry


def extract_todos(text: str) -> List[str]:
    """Find TODO items (started but not finished)."""
    patterns = [
        r"\*\*(?:Next|TODO|BLOCKED|In progress)\*\*:?\s+([^\n.]{5,200})",
        r"(?:^|\s)(?:Next|TODO|BLOCKED|In progress):?\s+([^\n.]{5,200})",
        r"^- (?:Next|TODO|BLOCKED|In progress):?\s+([^\n.]{5,200})",
    ]
    todos = []
    for p in patterns:
        for m in re.finditer(p, text, re.MULTILINE | re.IGNORECASE):
            t = m.group(1).strip()
            if t and t not in todos:
                todos.append(t)
    return todos


def extract_finished(text: str) -> List[str]:
    """Find 'done' items."""
    patterns = [
        r"- \[[xX]\]\s+([^\n]{1,150})",  # markdown task
        r"\[done\]\s+([^\n]{1,150})",
        r"shipped:?\s+([^\n.]{1,150})",
    ]
    items = []
    for p in patterns:
        for m in re.finditer(p, text, re.MULTILINE | re.IGNORECASE):
            items.append(m.group(1).strip())
    return items


def extract_facts(text: str) -> List[str]:
    """Find concrete factual statements (numbers, names)."""
    facts = []
    # Items with numbers
    for m in re.finditer(r"([^\n]{10,200})\b(\d+(?:/\d+)?)\s*(tests|repos|tools|pieces|cells|canon|fleets|tokens)\b", text):
        facts.append(m.group(0).strip()[:120])
    return facts[:50]


def extract_doctrine_anchors(text: str) -> List[str]:
    """Find doctrinal anchors."""
    return list(set(re.findall(r"`([a-z][a-z_0-9]{5,40})`", text)))


def review_session_work(work_text: str, session_name: str = "session") -> Dict:
    """Review a single session's work."""
    finished = extract_finished(work_text)
    todos = extract_todos(work_text)
    facts = extract_facts(work_text)
    doctrines = extract_doctrine_anchors(work_text)

    return {
        "session": session_name,
        "items_shipped": len(finished),
        "items_pending": len(todos),
        "facts_extracted": len(facts),
        "doctrines_referenced": doctrines,
    }


def review_productivity(memory_files: Dict[Path, str]) -> Dict:
    """Aggregate productivity across memory."""
    total_shipped = 0
    total_pending = 0
    doctrines_seen = set()
    facts_seen = []

    for path, text in memory_files.items():
        finished = extract_finished(text)
        todos = extract_todos(text)
        total_shipped += len(finished)
        total_pending += len(todos)
        doctrines_seen.update(extract_doctrine_anchors(text))
        facts_seen.extend(extract_facts(text))

    return {
        "files_analyzed": len(memory_files),
        "items_shipped": total_shipped,
        "items_pending": total_pending,
        "doctrines_seen": sorted(doctrines_seen),
        "fact_count": len(facts_seen),
        "shipping_rate": (total_shipped / (total_shipped + total_pending) * 100) if (total_shipped + total_pending) > 0 else 0,
    }


def identify_gaps(work_dirs: List[Path]) -> List[Dict]:
    """Find tools that exist but have incomplete features."""
    gaps = []
    for d in work_dirs:
        if not d.exists() or not d.is_dir():
            continue
        # Look for TODO/FIXME in code
        for py_file in list(d.rglob("*.py"))[:20]:
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(errors="replace")
                for m in re.finditer(r"#\s*(?:TODO|FIXME|XXX)\s*:?\s*([^\n]{5,100})", content):
                    gaps.append({
                        "repo": d.name,
                        "file": str(py_file.relative_to(d)),
                        "comment": m.group(1).strip(),
                    })
            except Exception:
                pass
    return gaps[:30]


def suggest_improvements(review: Dict, gaps: List[Dict]) -> List[Dict]:
    """Suggest concrete improvements based on review."""
    suggestions = []

    # High shipping rate + low pending = healthy
    if review.get("shipping_rate", 0) > 80:
        suggestions.append({
            "priority": "maintain",
            "name": "high shipping rate",
            "rationale": f"{review['shipping_rate']:.0f}% shipping rate — keep momentum",
        })

    # Many TODOs pending → block on closure
    if review.get("items_pending", 0) > review.get("items_shipped", 0):
        suggestions.append({
            "priority": "high",
            "name": "close pending items",
            "rationale": f"{review['items_pending']} pending vs {review['items_shipped']} shipped — backlog growing",
        })

    # Code TODOs
    code_gaps = sum(1 for g in gaps if g.get("file", "").endswith(".py"))
    if code_gaps > 5:
        suggestions.append({
            "priority": "medium",
            "name": "address code TODOs",
            "rationale": f"{code_gaps} TODO/FIXME comments in code",
        })

    # Doctrine coverage — if many doctrines not yet applied
    if len(review.get("doctrines_seen", [])) >= 5:
        suggestions.append({
            "priority": "low",
            "name": "doctrine expansion",
            "rationale": f"{len(review['doctrines_seen'])} doctrines referenced — opportunity to build tools for un-implemented ones",
        })

    return suggestions


def full_review(memory_dir: Optional[Path] = None, repos_dir: Optional[Path] = None) -> Dict:
    """Run a full self-review."""
    memory_files = {}
    if memory_dir and memory_dir.exists():
        for f in memory_dir.rglob("*.md"):
            try:
                memory_files[f] = f.read_text(errors="replace")
            except Exception:
                pass

    productivity = review_productivity(memory_files)

    gaps = []
    if repos_dir and repos_dir.exists():
        repo_dirs = [d for d in repos_dir.iterdir() if d.is_dir() and d.name.startswith(("quilt-canon-", "mavis-", "quilt-fleet-"))]
        gaps = identify_gaps(repo_dirs)

    suggestions = suggest_improvements(productivity, gaps)

    return {
        "productivity": productivity,
        "code_gaps": gaps,
        "suggestions": suggestions,
    }
