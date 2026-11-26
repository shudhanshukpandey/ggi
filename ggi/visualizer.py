"""
Export the memory graph as an interactive HTML visualisation using pyvis,
or as a static DOT / Mermaid diagram.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ggi.graph import MemoryGraph
from ggi.models import NodeKind


# ── Colour palette per node kind ─────────────────────────────────────────────

KIND_COLOURS: dict[str, str] = {
    NodeKind.FILE.value: "#4FC3F7",
    NodeKind.DIRECTORY.value: "#81C784",
    NodeKind.MODULE.value: "#AED581",
    NodeKind.FUNCTION.value: "#FFD54F",
    NodeKind.CLASS.value: "#FF8A65",
    NodeKind.CONCEPT.value: "#CE93D8",
    NodeKind.CHANGE.value: "#F06292",
    NodeKind.AGENT.value: "#90A4AE",
    NodeKind.ANNOTATION.value: "#FFF176",
}

KIND_SHAPES: dict[str, str] = {
    NodeKind.FILE.value: "dot",
    NodeKind.DIRECTORY.value: "triangle",
    NodeKind.MODULE.value: "diamond",
    NodeKind.FUNCTION.value: "square",
    NodeKind.CLASS.value: "star",
    NodeKind.CONCEPT.value: "hexagon",
    NodeKind.CHANGE.value: "triangleDown",
    NodeKind.AGENT.value: "box",
    NodeKind.ANNOTATION.value: "ellipse",
}


def to_pyvis_html(
    graph: MemoryGraph,
    output: str | Path = "memory_graph.html",
    height: str = "900px",
    width: str = "100%",
    notebook: bool = False,
) -> Path:
    """
    Render an interactive HTML visualisation via pyvis.

    Requires the ``viz`` extra: ``pip install ggi[viz]``
    """
    try:
        from pyvis.network import Network
    except ImportError as exc:
        raise ImportError(
            "pyvis is required for HTML export. Install with: pip install ggi[viz]"
        ) from exc

    net = Network(height=height, width=width, directed=True, notebook=notebook)
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=200)

    g = graph.graph
    for nid, attrs in g.nodes(data=True):
        kind = attrs.get("kind", "unknown")
        label = attrs.get("path", attrs.get("title", attrs.get("name", nid)))
        title_hover = _build_hover(nid, attrs)
        net.add_node(
            nid,
            label=str(label),
            title=title_hover,
            color=KIND_COLOURS.get(kind, "#BDBDBD"),
            shape=KIND_SHAPES.get(kind, "dot"),
            size=20 if kind == NodeKind.DIRECTORY.value else 12,
        )

    for u, v, attrs in g.edges(data=True):
        edge_label = attrs.get("label", attrs.get("kind", ""))
        net.add_edge(u, v, title=edge_label, label=edge_label, arrows="to")

    output = Path(output)
    net.save_graph(str(output))
    return output.resolve()


def to_mermaid(graph: MemoryGraph, direction: str = "TD") -> str:
    """
    Generate a Mermaid flowchart string.

    Parameters
    ----------
    direction : ``"TD"`` (top-down) or ``"LR"`` (left-right)
    """
    lines = [f"flowchart {direction}"]
    g = graph.graph

    for nid, attrs in g.nodes(data=True):
        kind = attrs.get("kind", "unknown")
        label = attrs.get("path", attrs.get("title", nid))
        safe_id = _mermaid_safe_id(nid)
        safe_label = str(label).replace('"', "'")

        if kind == NodeKind.DIRECTORY.value:
            lines.append(f'    {safe_id}["{safe_label} 📁"]')
        elif kind == NodeKind.CHANGE.value:
            lines.append(f'    {safe_id}("{safe_label} 🔧")')
        elif kind == NodeKind.AGENT.value:
            lines.append(f'    {safe_id}["{safe_label} 🤖"]')
        else:
            lines.append(f'    {safe_id}["{safe_label}"]')

    for u, v, attrs in g.edges(data=True):
        label = attrs.get("label", attrs.get("kind", ""))
        su, sv = _mermaid_safe_id(u), _mermaid_safe_id(v)
        if label:
            safe_label = str(label).replace('"', "'")
            lines.append(f'    {su} -->|"{safe_label}"| {sv}')
        else:
            lines.append(f"    {su} --> {sv}")

    return "\n".join(lines)


def to_dot(graph: MemoryGraph) -> str:
    """Generate a Graphviz DOT string."""
    lines = ["digraph MemoryGraph {", "    rankdir=LR;", '    node [fontname="Helvetica"];']
    g = graph.graph

    for nid, attrs in g.nodes(data=True):
        kind = attrs.get("kind", "unknown")
        label = attrs.get("path", attrs.get("title", nid))
        color = KIND_COLOURS.get(kind, "#BDBDBD")
        lines.append(f'    "{nid}" [label="{label}" fillcolor="{color}" style=filled];')

    for u, v, attrs in g.edges(data=True):
        label = attrs.get("label", "")
        lines.append(f'    "{u}" -> "{v}" [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_hover(nid: str, attrs: dict[str, Any]) -> str:
    """Build an HTML tooltip for pyvis."""
    parts = [f"<b>{nid}</b>"]
    for key in ("kind", "path", "language", "summary", "change_type", "description"):
        if key in attrs and attrs[key]:
            parts.append(f"<b>{key}:</b> {attrs[key]}")
    return "<br>".join(parts)


def _mermaid_safe_id(raw: str) -> str:
    """Convert a node ID to a Mermaid-safe identifier."""
    return raw.replace(":", "_").replace("/", "_").replace(".", "_").replace("-", "_")
