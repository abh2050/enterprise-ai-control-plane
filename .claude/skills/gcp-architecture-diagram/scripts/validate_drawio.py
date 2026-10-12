#!/usr/bin/env python3
"""Validate .drawio files built with this skill.

    python3 validate_drawio.py docs/diagrams/*.drawio

Checks: the XML parses and has no comments; root cells 0 and 1 exist; ids are unique;
every edge has a relative geometry and either a source and target cell or explicit end
points; every Google Cloud icon (shape=image with an SVG data URI) starts with an exact
style string from references/gcp-icons.json, followed by ";". Stdlib only.
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ICONS = Path(__file__).resolve().parents[1] / "references" / "gcp-icons.json"


def canonical_styles() -> list[str]:
    return [str(i["style"]) for i in json.loads(ICONS.read_text())]


def is_canonical(style: str, styles: list[str]) -> bool:
    """The style starts with a canonical icon style, ended by ";" before any overrides."""
    for s in styles:
        if style.startswith(s) and (s.endswith(";") or style[len(s) : len(s) + 1] in (";", "")):
            return True
    return False


def validate(path: Path, styles: list[str]) -> list[str]:
    errors: list[str] = []
    raw = path.read_text()
    if "<!--" in raw:
        errors.append("contains an XML comment")
    root = ET.fromstring(raw)
    cells = root.findall(".//mxCell")
    ids = [c.get("id") for c in cells]
    if "0" not in ids or "1" not in ids:
        errors.append("missing root cells 0 and 1")
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"duplicate ids: {sorted(dupes)}")
    known = set(ids)
    for c in cells:
        cid = c.get("id")
        style = c.get("style") or ""
        if c.get("edge") == "1":
            geo = c.find("mxGeometry")
            if geo is None or geo.get("relative") != "1":
                errors.append(f'edge {cid}: needs <mxGeometry relative="1">')
            has_cells = c.get("source") in known and c.get("target") in known
            has_points = geo is not None and {p.get("as") for p in geo.findall("mxPoint")} >= {
                "sourcePoint",
                "targetPoint",
            }
            if not (has_cells or has_points):
                errors.append(f"edge {cid}: no source and target")
        if "image=data:image/svg+xml," in style and not is_canonical(style, styles):
            errors.append(f"icon {cid}: style is not an exact Sidebar-GCP2.js icon style")
    return errors


def main(paths: list[str]) -> int:
    styles = canonical_styles()
    failed = 0
    for p in paths:
        errs = validate(Path(p), styles)
        for e in errs:
            print(f"{p}: {e}")
        failed += bool(errs)
    print(f"{len(paths) - failed} of {len(paths)} diagrams valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
