#!/usr/bin/env python3
"""Build a local A2 Key (KET) word index from Cambridge's official word list."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlretrieve


SOURCE_URL = "https://www.cambridgeenglish.org/images/506886-a2-key-2020-vocabulary-list.pdf"
ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "data" / "reference" / "ket-a2-vocabulary.json"
PARSE_ARTIFACTS = {"al", "zz"}


def extract_entries(text: str) -> list[dict[str, str]]:
    start = text.index("                     A                              allow")
    end = text.rindex("\fAppendix 1")
    entries: dict[str, dict[str, str]] = {}
    for line in text[start:end].splitlines():
        for column in (line[:52], line[52:]):
            value = column.strip()
            if not value or value.startswith("•") or re.fullmatch("[A-Z]", value):
                continue
            if value.startswith(("©", "A2 Key", "Schools", "Vocabulary List", "Key and Key")):
                continue
            headword = re.sub(r"\s+\([^)]*\)$", "", value).strip()
            part_of_speech = value[len(headword):].strip(" ()")
            if (
                not re.search(r"[a-z]", headword)
                or not re.match(r"^[A-Za-z]", headword)
                or any(character in headword for character in ".!?,:;")
                or len(headword) > 45
                or "A2 Key" in headword
                or headword in {"for", "Schools", "and Key for"} | PARSE_ARTIFACTS
            ):
                continue
            key = headword.lower()
            entries.setdefault(key, {
                "id": hashlib.sha1(key.encode()).hexdigest()[:12],
                "word": headword,
                "part_of_speech": part_of_speech,
                "letter": headword[0].upper(),
                "source": "Cambridge A2 Key Vocabulary List, August 2025",
            })
    return sorted(entries.values(), key=lambda item: item["word"].lower())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, help="Use an already downloaded official PDF")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        pdf = args.pdf or Path(directory) / "a2-key-vocabulary-list.pdf"
        if not args.pdf:
            urlretrieve(SOURCE_URL, pdf)
        text_path = Path(directory) / "word-list.txt"
        subprocess.run(["pdftotext", "-layout", str(pdf), str(text_path)], check=True)
        entries = extract_entries(text_path.read_text(encoding="utf-8"))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps({"source_url": SOURCE_URL, "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Imported {len(entries)} A2 Key entries into {TARGET}")


if __name__ == "__main__":
    main()
