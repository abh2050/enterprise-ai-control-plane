---
name: gcp-architecture-diagram
description: Generate Google Cloud architecture diagrams as draw.io files with Google's official icons and export them to PNG. Use when asked to create or update an architecture, system, or flow diagram for Google Cloud services in this repository.
---

## How diagrams are made here

Diagrams are Python sources that place every element by coordinate, built with
`scripts/drawio.py` (stdlib only). `docs/diagrams/build.py` writes each
`docs/diagrams/NN_name.drawio` and exports a 2x PNG with the draw.io desktop CLI
(`brew install --cask drawio`). Never hand-edit the `.drawio` files; change the source and rebuild:

    python3 docs/diagrams/build.py            # all
    python3 docs/diagrams/build.py 02 07      # some
    python3 .claude/skills/gcp-architecture-diagram/scripts/validate_drawio.py docs/diagrams/*.drawio

Then open every changed PNG and look at it. Fix overlaps in the source and rebuild.

## Icons: never guess

- `Page.icon(key, "<exact name>", x, y, label, size=52, side="bottom"|"top"|"right")`
- Names come from `references/gcp-icons.json` (187 icons, plus the per-category Markdown
  files). These are draw.io's own style strings from `Sidebar-GCP2.js`, copied byte for
  byte by `scripts/extract_icons.py` at the commit pinned in `SOURCE.md`;
  `tests/test_gcp_diagrams.py` re-extracts and compares.
- The builder appends label overrides after the canonical string and always inserts a
  `;` first: five canonical styles (Artifact Registry among them) end in base64 `==`
  without one, and appending directly corrupts the image.
- Identity-Aware Proxy exists only as a product-card icon; it is extracted the same way.

## Layout rules (adapted from the aws-architecture-diagram skill)

- Left to right for the request path; people and clients on the left; data stores on the right.
- Lanes: one row per path, at least 220 px between icons horizontally and 120 px between rows.
- Containers: Google Cloud project (`zone(..., fill="project")`), inner zones from the
  Project Zone palette fills, managed services as the dashed blue zone. Add zones before
  their contents (z-order).
- Labels must never be crossed by an edge. If an edge leaves an icon on a side, put that
  icon's label on another side (`side="top"` or `"right"`), or use offset ports (`"B:0.2"`).
- Edge label on the segment it describes; shared trunks carry no label; use `label_pos`.
- Long rule lists go in `note(...)`, connected with an `optional_secondary` edge.
- Every diagram gets the blue GCP title bar (title and a one-line subtitle naming its
  evidence file) and a legend listing only the path kinds it uses.

## Path kinds (draw.io GCP Paths palette)

| kind | meaning |
|---|---|
| primary | request or data path |
| optional | optional path |
| secondary | scheduled or supporting path |
| optional_secondary | configuration or rule input |
| success | allowed or settled |
| failure | blocked or failed |

## Numbers

A number in a diagram must appear in a file under `docs/` or `configs/`; list the source
in `docs/diagrams/README.md`. Do not round or restate a measured number differently.
