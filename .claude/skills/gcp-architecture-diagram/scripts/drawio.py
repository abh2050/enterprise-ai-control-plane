"""Build Google Cloud architecture diagrams as .drawio files with explicit coordinates.

Every Google Cloud icon starts with the exact style string draw.io ships
(references/gcp-icons.json); zones, paths, cards, and the title bar start with the
exact strings from draw.io's GCP palettes. Overrides (font size, label position) are
appended, so the canonical string stays intact and draw.io applies the last value.
Stdlib only.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from xml.sax.saxutils import quoteattr

ICONS = Path(__file__).resolve().parents[1] / "references" / "gcp-icons.json"

# draw.io GCP palettes (Sidebar-GCP2.js), byte for byte.
ZONE = (
    "shape=rect;strokeColor=none;strokeWidth=2;shadow=0;gradientColor=none;fontColor=#757575;"
    "align=left;html=1;fontStyle=0;spacingTop=3;fillColor={fill};verticalAlign=top;fontSize=10;"
    "spacingLeft=10;spacing=0;"
)
DASHED_ZONE = (
    "rounded=1;absoluteArcSize=1;arcSize=2;html=1;strokeColor=none;gradientColor=none;shadow=0;"
    "dashed=1;strokeColor=#4284F3;fontSize=10;fontColor=#9E9E9E;align=left;verticalAlign=top;"
    "spacing=0;spacingTop=3;fillColor=none;dashPattern=1 2;strokeWidth=2;fontStyle=0;spacingLeft=10;"
)
PATH = "edgeStyle=orthogonalEdgeStyle;fontSize=12;html=1;endArrow=blockThin;endFill=1;rounded=0;strokeWidth=2;endSize=4;startSize=4;"
PATHS = {
    "primary": PATH + "dashed=0;strokeColor=#4284F3;",
    "optional": PATH + "dashed=1;dashPattern=1 3;strokeColor=#4284F3;",
    "secondary": PATH + "dashed=0;strokeColor=#9E9E9E;",
    "optional_secondary": PATH + "dashed=1;dashPattern=1 3;strokeColor=#9E9E9E;",
    "success": PATH + "strokeColor=#34A853;dashed=0;",
    "failure": PATH + "strokeColor=#EA4335;dashed=0;",
}
CARD = "fillColor=#ffffff;strokeColor=#dddddd;shadow=1;strokeWidth=1;rounded=1;absoluteArcSize=1;arcSize=2;"
TITLE_BAR = (
    "fillColor=#4DA1F5;strokeColor=none;shadow=1;gradientColor=none;fontSize=14;align=left;"
    "spacingLeft=50;fontColor=#ffffff;whiteSpace=wrap;html=1;"
)

# Zone fills from the Project Zone template.
FILLS = {
    "project": "#F6F6F6",
    "blue": "#E3F2FD",
    "orange": "#FFF3E0",
    "purple": "#EDE7F6",
    "pink": "#FCE4EC",
    "green": "#E8F5E9",
    "indigo": "#E8EAF6",
    "grey": "#ECEFF1",
    "white": "#FFFFFF",
}
INK = "#3C4043"
LABEL = f"fontSize=13;fontStyle=0;fontColor={INK};"
ICON_LABEL = (
    LABEL
    + "verticalLabelPosition=bottom;verticalAlign=top;labelPosition=center;align=center;spacingTop=2;"
)
ICON_LABEL_TOP = (
    LABEL
    + "verticalLabelPosition=top;verticalAlign=bottom;labelPosition=center;align=center;spacingBottom=2;"
)
ICON_LABEL_RIGHT = (
    LABEL
    + "verticalLabelPosition=middle;verticalAlign=middle;labelPosition=right;align=left;spacingLeft=10;"
)
ACCENTS = {
    "step": None,
    "decision": "#4284F3",
    "ok": "#34A853",
    "bad": "#EA4335",
    "muted": "#9E9E9E",
}
PORTS = {"R": (1, 0.5), "L": (0, 0.5), "T": (0.5, 0), "B": (0.5, 1)}


def load_icons() -> dict[str, dict[str, object]]:
    found: dict[str, dict[str, object]] = {}
    for icon in json.loads(ICONS.read_text()):
        found.setdefault(str(icon["name"]), icon)
    return found


class Page:
    def __init__(self, title: str, width: int, height: int, subtitle: str = "") -> None:
        self.width, self.height = width, height
        self.cells: list[str] = []
        self.ids: set[str] = set()
        self.icons = load_icons()
        self._n = 0
        self._vertex(
            "bg",
            "",
            "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=none;",
            0,
            0,
            width,
            height,
        )
        head = f"<b>{escape(title)}</b>" + (
            f'<br><font style="font-size:13px">{escape(subtitle)}</font>' if subtitle else ""
        )
        self._vertex(
            "title",
            head,
            TITLE_BAR + "fontSize=20;spacingLeft=24;verticalAlign=middle;",
            0,
            0,
            width,
            64 if subtitle else 52,
        )

    # Low-level

    def _id(self, key: str | None) -> str:
        if key is None:
            self._n += 1
            key = f"c{self._n}"
        if key in self.ids:
            raise ValueError(f"duplicate id {key}")
        self.ids.add(key)
        return key

    def _vertex(
        self,
        key: str | None,
        value: str,
        style: str,
        x: float,
        y: float,
        w: float,
        h: float,
        parent: str = "1",
    ) -> str:
        cid = self._id(key)
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(value)} style={quoteattr(style)} vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" as="geometry"/></mxCell>'
        )
        return cid

    # Shapes

    def zone(
        self,
        label: str,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str = "project",
        dashed: bool = False,
        align: str = "left",
    ) -> str:
        """A container drawn behind its contents (add zones before what sits in them)."""
        style = DASHED_ZONE if dashed else ZONE.format(fill=FILLS[fill])
        style += "fontSize=13;fontColor=#5F6368;spacingTop=6;"
        if align == "right":
            style += "align=right;spacingRight=12;"
        return self._vertex(None, f"<b>{escape(label)}</b>", style, x, y, w, h)

    def icon(
        self,
        key: str,
        product: str,
        x: float,
        y: float,
        label: str,
        size: float = 52,
        side: str = "bottom",
    ) -> str:
        """A Google Cloud product icon; (x, y) is its top-left corner; label below, above, or right."""
        spec = self.icons.get(product)
        if spec is None:
            raise KeyError(f"no icon named {product!r} in references/gcp-icons.json")
        w, h = float(spec["width"]), float(spec["height"])  # type: ignore[arg-type]
        scale = size / max(w, h)
        # Center the icon in a size x size box, so icons of any aspect share centers.
        x += (size - w * scale) / 2
        y += (size - h * scale) / 2
        placement = {"right": ICON_LABEL_RIGHT, "top": ICON_LABEL_TOP}.get(side, ICON_LABEL)
        base = str(spec["style"])
        # Some canonical styles end without ";" (Artifact Registry's ends in base64 "=="):
        # appending directly would corrupt the image data.
        if not base.endswith(";"):
            base += ";"
        return self._vertex(key, text(label), base + placement, x, y, w * scale, h * scale)

    def card(
        self,
        key: str,
        label: str,
        x: float,
        y: float,
        w: float = 200,
        h: float = 64,
        kind: str = "step",
    ) -> str:
        """A process step: a white GCP card; colored border for decisions and outcomes."""
        style = CARD + LABEL + "whiteSpace=wrap;html=1;align=center;verticalAlign=middle;spacing=8;"
        accent = ACCENTS[kind]
        if accent:
            style += f"strokeColor={accent};strokeWidth=2;"
        if kind == "muted":
            style += "fillColor=#F8F9FA;fontColor=#5F6368;dashed=1;"
        return self._vertex(key, text(label), style, x, y, w, h)

    def table(
        self,
        key: str,
        title: str,
        fields: list[tuple[str, str, str]],
        x: float,
        y: float,
        w: float = 330,
        header: str = "#4284F3",
        subtitle: str = "",
    ) -> dict[str, str]:
        """An entity table: a header and one row per field (name, type, tags).

        Tags: "PK" (MERGE key, bold), "FK" (join column, italic), "PART" (partition),
        "CLUSTER" (cluster), space separated. Returns {field name: row cell id} so
        relations can attach to a specific column.
        """
        row_h, head_h = 24, (48 if subtitle else 32)
        title_html = f"<b>{escape(title)}</b>"
        if subtitle:
            title_html += (
                f'<br><span style="font-size:11px;font-weight:normal">{escape(subtitle)}</span>'
            )
        style = (
            "swimlane;html=1;whiteSpace=wrap;container=1;collapsible=0;"
            f"horizontal=1;startSize={head_h};"
            f"fillColor={header};strokeColor={header};fontColor=#FFFFFF;fontSize=14;align=center;"
            "rounded=1;arcSize=6;absoluteArcSize=1;swimlaneFillColor=#FFFFFF;shadow=1;"
        )
        tid = self._vertex(key, title_html, style, x, y, w, head_h + row_h * len(fields))
        rows: dict[str, str] = {}
        for i, (name, typ, tags) in enumerate(fields):
            shown = escape(name)
            if "PK" in tags.split():
                shown = f"<b>{shown}</b>"
            if "FK" in tags.split():
                shown = f"<i>{shown}</i>"
            if tags:
                shown += f' <font style="font-size:10px" color="#1A73E8">{escape(tags)}</font>'
            keyed = bool({"PK", "FK", "KEY"} & set(tags.split()))
            fill = "#EEF4FE" if keyed else "#FFFFFF"
            row_style = (
                f"text;html=1;strokeColor=#E8EAED;fillColor={fill};align=left;verticalAlign=middle;"
                "spacingLeft=10;spacingRight=10;overflow=hidden;rotatable=0;fontSize=12;"
                f"fontColor={INK};whiteSpace=wrap;"
            )
            row = self._vertex(
                f"{key}.{name}", shown, row_style, 0, head_h + i * row_h, w, row_h, parent=tid
            )
            type_style = (
                "text;html=1;strokeColor=none;fillColor=none;align=right;verticalAlign=middle;"
                "spacingRight=10;fontSize=11;fontColor=#80868B;"
            )
            self._vertex(None, escape(typ), type_style, w - 110, 0, 110, row_h, parent=row)
            rows[name] = row
        return rows

    def relation(
        self,
        src: str,
        dst: str,
        out: str = "R",
        into: str = "L",
        points: list[tuple[float, float]] | None = None,
        label: str = "",
        label_pos: float | None = None,
    ) -> str:
        """A many-to-one join between two table rows: crow's foot at the many end."""
        cid = self._id(None)
        ex, ey = port(out)
        nx, ny = port(into)
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeWidth=1.5;strokeColor=#5F6368;"
            "startArrow=ERmany;startFill=0;endArrow=ERmandOne;endFill=0;startSize=12;endSize=12;"
            f"exitX={ex:g};exitY={ey:g};exitDx=0;exitDy=0;entryX={nx:g};entryY={ny:g};"
            f"entryDx=0;entryDy=0;labelBackgroundColor=#FFFFFF;fontSize=11;fontColor={INK};"
        )
        value = f" value={quoteattr(text(label))}" if label else ""
        pts = ""
        if points:
            pts = (
                '<Array as="points">'
                + "".join(f'<mxPoint x="{px:g}" y="{py:g}"/>' for px, py in points)
                + "</Array>"
            )
        self.cells.append(
            f'<mxCell id="{cid}"{value} style={quoteattr(style)} edge="1" parent="1" '
            f'source="{src}" target="{dst}"><mxGeometry relative="1"'
            + (f' x="{label_pos:g}"' if label_pos is not None else "")
            + f' as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return cid

    def note(self, key: str | None, label: str, x: float, y: float, w: float, h: float) -> str:
        style = (
            "shape=note;size=14;whiteSpace=wrap;html=1;fillColor=#FFFDE7;strokeColor=#E6D28A;"
            f"align=left;verticalAlign=top;spacingLeft=10;spacingTop=6;fontSize=12;fontColor={INK};"
        )
        return self._vertex(key, text(label), style, x, y, w, h)

    def text(
        self,
        label: str,
        x: float,
        y: float,
        w: float,
        h: float,
        size: int = 12,
        color: str = "#5F6368",
        align: str = "left",
    ) -> str:
        style = f"text;html=1;whiteSpace=wrap;align={align};verticalAlign=top;fontSize={size};fontColor={color};"
        return self._vertex(None, text(label), style, x, y, w, h)

    def edge(
        self,
        src: str,
        dst: str,
        label: str = "",
        kind: str = "primary",
        out: str = "R",
        into: str = "L",
        points: list[tuple[float, float]] | None = None,
        label_pos: float | None = None,
    ) -> str:
        cid = self._id(None)
        ex, ey = port(out)
        nx, ny = port(into)
        style = (
            PATHS[kind]
            + f"exitX={ex:g};exitY={ey:g};exitDx=0;exitDy=0;entryX={nx:g};entryY={ny:g};entryDx=0;entryDy=0;"
            + f"labelBackgroundColor=#FFFFFF;fontColor={INK};fontSize=12;"
        )
        value = f" value={quoteattr(text(label))}" if label else ""
        pts = ""
        if points:
            pts = (
                '<Array as="points">'
                + "".join(f'<mxPoint x="{px:g}" y="{py:g}"/>' for px, py in points)
                + "</Array>"
            )
        offset = f' x="{label_pos:g}"' if label_pos is not None else ""
        self.cells.append(
            f'<mxCell id="{cid}"{value} style={quoteattr(style)} edge="1" parent="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1"{offset} as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return cid

    def legend(
        self,
        x: float,
        y: float,
        kinds: tuple[str, ...] = ("primary", "secondary", "success", "failure"),
    ) -> None:
        names = {
            "primary": "Request or data path",
            "optional": "Optional path",
            "secondary": "Scheduled or supporting path",
            "optional_secondary": "Configuration or rule input",
            "success": "Allowed or settled",
            "failure": "Blocked or failed",
        }
        self.zone("Legend", x, y, 250, 40 + 26 * len(kinds), fill="white")
        for i, k in enumerate(kinds):
            yy = y + 44 + 26 * i
            cid = self._id(None)
            self.cells.append(
                f'<mxCell id="{cid}" style={quoteattr(PATHS[k] + "edgeStyle=none;")} edge="1" parent="1">'
                f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x + 14:g}" y="{yy:g}" as="sourcePoint"/>'
                f'<mxPoint x="{x + 64:g}" y="{yy:g}" as="targetPoint"/></mxGeometry></mxCell>'
            )
            self.text(names[k], x + 74, yy - 9, 170, 20, 12, INK)

    def write(self, path: Path) -> None:
        body = "".join(self.cells)
        xml = (
            '<mxfile host="drawio" type="device">'
            f'<diagram id="{path.stem}" name="{escape(path.stem)}">'
            f'<mxGraphModel dx="{self.width}" dy="{self.height}" grid="0" gridSize="10" guides="1" tooltips="1" '
            f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" '
            'math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            f"{body}</root></mxGraphModel></diagram></mxfile>\n"
        )
        path.write_text(xml)


def port(spec: str) -> tuple[float, float]:
    """A side ("R", "L", "T", "B"), optionally with a position along it: "B:0.3"."""
    side, _, along = spec.partition(":")
    x, y = PORTS[side]
    if along:
        if side in ("T", "B"):
            x = float(along)
        else:
            y = float(along)
    return x, y


def text(label: str) -> str:
    """Plain text to draw.io HTML: escape, keep <b> emphasis, newlines become line breaks."""
    html = escape(label).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    return html.replace("\n", "<br>")
