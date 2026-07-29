from __future__ import annotations

import re
from pathlib import Path


MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_local_markdown_links_resolve():
    missing = []

    for document in Path(".").rglob("*.md"):
        if any(part.startswith(".") for part in document.parts):
            continue

        content = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(content):
            target = target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "../")):
                continue

            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{document}: {target}")

    assert not missing, "Missing local Markdown links:\n" + "\n".join(missing)
