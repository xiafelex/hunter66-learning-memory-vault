#!/usr/bin/env python3
"""Build a lightweight weekly review draft from Markdown front matter."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = DATA / "reports"


def parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def collect_records() -> list[tuple[Path, dict[str, str]]]:
    records: list[tuple[Path, dict[str, str]]] = []
    for path in DATA.rglob("*.md"):
        if "reports" in path.parts:
            continue
        meta = parse_front_matter(path)
        if meta:
            records.append((path, meta))
    return records


def main() -> None:
    today = dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())
    week_end = week_start + dt.timedelta(days=6)
    records = collect_records()

    by_type: dict[str, list[tuple[Path, dict[str, str]]]] = {}
    for path, meta in records:
        by_type.setdefault(meta.get("type", "unknown"), []).append((path, meta))

    lines = [
        "---",
        "type: weekly_report",
        "student: Hunter 六六",
        f"week_start: {week_start.isoformat()}",
        f"week_end: {week_end.isoformat()}",
        "status: draft",
        "---",
        "",
        f"# 周复盘 {week_start.isoformat()} 至 {week_end.isoformat()}",
        "",
        "## 本周记录概览",
        "",
    ]

    labels = {
        "teacher_requirement": "老师要求",
        "wrong_question": "错题",
        "knowledge_point": "知识点",
        "weakness": "薄弱点",
    }
    for record_type, label in labels.items():
        items = by_type.get(record_type, [])
        lines.append(f"- {label}: {len(items)} 条")

    lines.extend(["", "## 需要复习的记录", ""])
    due_items = []
    for path, meta in records:
        next_review = meta.get("next_review", "")
        if next_review and next_review <= today.isoformat():
            due_items.append((path, meta))

    if due_items:
        for path, meta in sorted(due_items, key=lambda item: str(item[0])):
            rel = path.relative_to(ROOT)
            title = meta.get("knowledge_point") or meta.get("weakness") or path.stem
            lines.append(f"- [{title}](../../{rel})")
    else:
        lines.append("- 暂无到期复习记录。")

    lines.extend(
        [
            "",
            "## 本周最重要发现",
            "",
            "- ",
            "",
            "## 下周重点",
            "",
            "- ",
            "",
            "## 给六六的话",
            "",
            "",
        ]
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"{week_start.isoformat()}-weekly-review.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
