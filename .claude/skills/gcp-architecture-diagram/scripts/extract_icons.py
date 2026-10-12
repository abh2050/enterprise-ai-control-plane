#!/usr/bin/env python3
"""Extract Google Cloud icon styles from draw.io's Sidebar-GCP2.js, byte for byte.

    python3 extract_icons.py [path/to/Sidebar-GCP2.js]

With no path, downloads the file at the commit pinned in ../SOURCE.md. Every
`createVertexTemplateEntry(n + '<style>', s * W, s * H, '<label>', ...)` in the
`addGCP2Icons*Palette` functions becomes one entry: the palette's style prefix `n`
concatenated with the entry's own string, unchanged. Products that only appear as
product cards (Identity-Aware Proxy, for one) get the card's icon style the same way.
Writes references/gcp-icons.json
(the index the diagram builder reads) and one Markdown file per category.
Stdlib only.
"""

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REFS = SKILL / "references"
SOURCE_MD = SKILL / "SOURCE.md"
URL = "https://raw.githubusercontent.com/jgraph/drawio/{sha}/src/main/webapp/js/diagramly/sidebar/Sidebar-GCP2.js"

PALETTE = re.compile(
    r"Sidebar\.prototype\.addGCP2Icons(\w+)Palette = function\(\)(.*?)\n\t\};", re.S
)
PREFIX = re.compile(r"var n = '([^']*)';")
CARD_PREFIX = re.compile(
    r"Sidebar\.prototype\.addGCP2UserProductCard = function.*?var s = '([^']*)';", re.S
)
CARD_PALETTE = re.compile(
    r"Sidebar\.prototype\.addGCP2(\w+)Palette = function\(\)(.*?)\n\t\};", re.S
)
CARD = re.compile(
    r"icon = '([^']*)';\s*this\.addGCP2UserProductCardSet\('([^']*)', [\d.]+, [\d.]+, [\d.]+, ([\d.]+), ([\d.]+),"
)
ENTRY = re.compile(
    r"this\.createVertexTemplateEntry\(n \+ '([^']*)',\s*s \* ([\d.]+), s \* ([\d.]+), '([^']*)'"
)


def pinned() -> tuple[str, str]:
    text = SOURCE_MD.read_text()
    sha = re.search(r"Commit: ([0-9a-f]{40})", text)
    digest = re.search(r"SHA-256: ([0-9a-f]{64})", text)
    if not sha or not digest:
        raise SystemExit("SOURCE.md must name the pinned commit and the file's SHA-256")
    return sha.group(1), digest.group(1)


def load(path: str | None) -> bytes:
    sha, digest = pinned()
    data = Path(path).read_bytes() if path else urllib.request.urlopen(URL.format(sha=sha)).read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise SystemExit("Sidebar-GCP2.js does not match the SHA-256 pinned in SOURCE.md")
    return data


def extract(data: bytes) -> list[dict[str, object]]:
    """Standalone icons first; product-card icons only for products that lack one."""
    text = data.decode("utf-8")
    icons: list[dict[str, object]] = []
    for category, body in PALETTE.findall(text):
        prefix = PREFIX.search(body)
        if not prefix:
            continue
        for style, w, h, label in ENTRY.findall(body):
            icons.append(entry(category, label, w, h, prefix.group(1) + style, "icon"))
    card_prefix = CARD_PREFIX.search(text)
    if card_prefix:
        have = {i["name"] for i in icons}
        for category, body in CARD_PALETTE.findall(text):
            if category.startswith("Icons"):
                continue
            for svg, label, iw, ih in CARD.findall(body):
                item = entry(category, label, iw, ih, card_prefix.group(1) + svg, "card")
                if item["name"] not in have:
                    icons.append(item)
                    have.add(item["name"])
    return icons


def entry(category: str, label: str, w: str, h: str, style: str, kind: str) -> dict[str, object]:
    return {
        "category": category,
        "name": " ".join(label.replace("\\n", " ").split()),
        "kind": kind,
        "width": float(w),
        "height": float(h),
        "style": style,
    }


def write(icons: list[dict[str, object]]) -> None:
    REFS.mkdir(exist_ok=True)
    (REFS / "gcp-icons.json").write_text(json.dumps(icons, indent=1) + "\n")
    by_cat: dict[str, list[dict[str, object]]] = {}
    for icon in icons:
        by_cat.setdefault(str(icon["category"]), []).append(icon)
    for cat, items in sorted(by_cat.items()):
        lines = [
            f"# Google Cloud icons: {cat}",
            "",
            "Copied byte for byte from Sidebar-GCP2.js (see ../SOURCE.md).",
            "",
        ]
        for i in items:
            digest = hashlib.sha256(str(i["style"]).encode()).hexdigest()[:16]
            lines += [
                f"## {i['name']}",
                f"- size: {i['width']:g} x {i['height']:g}",
                f"- style sha256: `{digest}`",
                "",
            ]
        (REFS / f"gcp-icons-{cat.lower()}.md").write_text("\n".join(lines))


if __name__ == "__main__":
    found = extract(load(sys.argv[1] if len(sys.argv) > 1 else None))
    if not found:
        raise SystemExit("no icons found: the sidebar format changed")
    write(found)
    print(
        f"{len(found)} icons in {len({i['category'] for i in found})} categories", file=sys.stderr
    )
