"""
CLI for GGI — scan, inspect, export, and query memory graphs from the terminal.

Usage::

    ggi scan .                     # scan current directory
    ggi scan ./my-project -o graph.json
    ggi show graph.json            # print stats
    ggi show graph.json --node <id>
    ggi export graph.json --html   # interactive HTML
    ggi export graph.json --mermaid
    ggi export graph.json --dot
    ggi context graph.json <node>  # rich context for an agent
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ggi import __version__
from ggi.graph import MemoryGraph
from ggi.models import NodeKind
from ggi.scanner import scan_directory
from ggi.serializer import load_graph, save_graph

console = Console()


@click.group()
@click.version_option(__version__, prog_name="ggi")
def cli() -> None:
    """GGI — Graph-based General Intelligence Memory."""


# ── scan ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", default="memory_graph.json", help="Output file path.")
@click.option("--name", default=None, help="Project name (defaults to dir name).")
@click.option("--depth", default=None, type=int, help="Max scan depth.")
@click.option("--format", "fmt", type=click.Choice(["json", "yaml"]), default="json")
@click.option("--no-hash", is_flag=True, help="Skip content hashing (faster).")
def scan(
    directory: str,
    output: str,
    name: str | None,
    depth: int | None,
    fmt: str,
    no_hash: bool,
) -> None:
    """Scan a directory and build a memory graph."""
    console.print(f"[bold blue]Scanning[/] {directory} …")
    mg = scan_directory(
        directory,
        project_name=name,
        max_depth=depth,
        include_content_hash=not no_hash,
    )
    out = save_graph(mg, output, fmt=fmt)
    console.print(f"[green]✓[/] {mg.summary()}")
    console.print(f"[dim]Saved to {out}[/]")


# ── show ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("graph_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--node", default=None, help="Show details for a specific node ID.")
@click.option("--kind", default=None, help="Filter nodes by kind.")
@click.option("--search", default=None, help="Search nodes by path substring.")
def show(graph_file: str, node: str | None, kind: str | None, search: str | None) -> None:
    """Display stats or query a memory graph."""
    mg = load_graph(graph_file)

    if node:
        data = mg.get_node(node)
        if data is None:
            console.print(f"[red]Node '{node}' not found[/]")
            sys.exit(1)
        console.print_json(json.dumps(data, indent=2, default=str))
        return

    if kind or search:
        nk = NodeKind(kind) if kind else None
        results = mg.find_nodes(kind=nk, path_contains=search)
        table = Table(title=f"Query results ({len(results)})")
        table.add_column("ID", style="cyan")
        table.add_column("Kind")
        table.add_column("Path / Title")
        table.add_column("Language")
        for r in results:
            table.add_row(
                r.get("id", ""),
                r.get("kind", ""),
                r.get("path", r.get("title", "")),
                r.get("language", ""),
            )
        console.print(table)
        return

    # Default: show stats
    stats = mg.stats()
    console.print(f"\n[bold]{mg.summary()}[/]\n")

    table = Table(title="Node kinds")
    table.add_column("Kind", style="cyan")
    table.add_column("Count", justify="right")
    for k, v in sorted(stats["node_kinds"].items()):
        table.add_row(k, str(v))
    console.print(table)

    if stats["edge_kinds"]:
        table2 = Table(title="Edge kinds")
        table2.add_column("Kind", style="green")
        table2.add_column("Count", justify="right")
        for k, v in sorted(stats["edge_kinds"].items()):
            table2.add_row(k, str(v))
        console.print(table2)


# ── context ──────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("graph_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("node_id")
@click.option("--depth", default=2, type=int, help="Neighbourhood depth.")
@click.option("--json-out", is_flag=True, help="Output raw JSON instead of pretty print.")
def context(graph_file: str, node_id: str, depth: int, json_out: bool) -> None:
    """Extract rich context for a node — designed for agent hand-off."""
    mg = load_graph(graph_file)
    ctx = mg.context_for(node_id, depth=depth)

    if "error" in ctx:
        console.print(f"[red]{ctx['error']}[/]")
        sys.exit(1)

    if json_out:
        console.print_json(json.dumps(ctx, indent=2, default=str))
        return

    # Pretty print
    node_data = ctx["node"]
    console.print(f"\n[bold cyan]Node:[/] {node_data.get('path', node_id)}")
    console.print(f"  Kind: {node_data.get('kind')}  |  Language: {node_data.get('language', '—')}")
    if node_data.get("summary"):
        console.print(f"  Summary: {node_data['summary']}")

    if ctx["changes"]:
        console.print(f"\n[bold magenta]Changes ({len(ctx['changes'])}):[/]")
        for ch in ctx["changes"]:
            icon = "🔧" if ch.get("change_type") == "correction" else "✨"
            console.print(f"  {icon} {ch.get('title', ch.get('id'))}: {ch.get('description', '')}")

    if ctx["annotations"]:
        console.print(f"\n[bold yellow]Annotations ({len(ctx['annotations'])}):[/]")
        for ann in ctx["annotations"]:
            console.print(f"  📝 {ann.get('text', '')}")

    console.print(f"\n  Incoming edges: {len(ctx['incoming'])}  |  Outgoing edges: {len(ctx['outgoing'])}")


# ── export ───────────────────────────────────────────────────────────────────


@cli.command(name="export")
@click.argument("graph_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--interactive", "as_interactive", is_flag=True, help="Self-contained interactive HTML web app with Q&A panel.")
@click.option("--html", "as_html", is_flag=True, help="Pyvis network HTML.")
@click.option("--mermaid", "as_mermaid", is_flag=True, help="Mermaid flowchart.")
@click.option("--dot", "as_dot", is_flag=True, help="Graphviz DOT.")
@click.option("-o", "--output", default=None, help="Output file (HTML/DOT/MMD).")
def export_cmd(
    graph_file: str,
    as_interactive: bool,
    as_html: bool,
    as_mermaid: bool,
    as_dot: bool,
    output: str | None,
) -> None:
    """Export a memory graph as Interactive Web App, Pyvis HTML, Mermaid, or DOT."""
    from ggi.visualizer import to_dot, to_interactive_html, to_mermaid, to_pyvis_html

    mg = load_graph(graph_file)

    if as_interactive or (not as_html and not as_mermaid and not as_dot):
        out = to_interactive_html(mg, output=output or f"{Path(graph_file).stem}_interactive.html")
        console.print(f"[green]✓[/] Interactive Graph + Q&A Web App saved to [bold cyan]{out}[/]")
    elif as_html:
        out = to_pyvis_html(mg, output=output or "memory_graph.html")
        console.print(f"[green]✓[/] Pyvis HTML saved to {out}")
    elif as_mermaid:
        mmd = to_mermaid(mg)
        if output:
            Path(output).write_text(mmd)
            console.print(f"[green]✓[/] Mermaid saved to {output}")
        else:
            console.print(mmd)
    elif as_dot:
        dot = to_dot(mg)
        if output:
            Path(output).write_text(dot)
            console.print(f"[green]✓[/] DOT saved to {output}")
        else:
            console.print(dot)


# ── ask (Q&A CLI) ────────────────────────────────────────────────────────────


@cli.command()
@click.argument("graph_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("question")
@click.option("--slm-url", default=None, help="Optional Ollama/SLM endpoint, e.g. http://localhost:11434")
@click.option("--json-out", is_flag=True, help="Output response as raw JSON.")
def ask(graph_file: str, question: str, slm_url: str | None, json_out: bool) -> None:
    """Ask a question about the codebase using graph intelligence."""
    from ggi.qa import GraphQA

    mg = load_graph(graph_file)
    qa = GraphQA(mg, slm_url=slm_url)
    res = qa.ask(question)

    if json_out:
        console.print_json(json.dumps(res, indent=2, default=str))
        return

    console.print(f"\n[bold cyan]Question:[/] {question}\n")
    console.print(f"[bold green]Answer:[/]\n{res['answer']}\n")

    if res.get("cited_nodes"):
        console.print("[dim]Cited Graph Nodes:[/]")
        for nid in res["cited_nodes"]:
            ndata = mg.get_node(nid) or {}
            label = ndata.get("path", ndata.get("title", nid))
            console.print(f"  • [cyan]{label}[/] ([dim]{ndata.get('kind', 'node')}[/])")


# ── ui (Interactive Server) ──────────────────────────────────────────────────


@cli.command()
@click.argument("graph_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--port", default=8501, type=int, help="Port to serve on (default: 8501).")
@click.option("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1).")
@click.option("--no-open", is_flag=True, help="Do not automatically open browser.")
@click.option("--slm-url", default=None, help="Optional Ollama/SLM URL for enhanced reasoning.")
def ui(graph_file: str, port: int, host: str, no_open: bool, slm_url: str | None) -> None:
    """Launch the interactive web UI and question panel in your browser."""
    from ggi.server import start_server

    start_server(
        graph_file,
        port=port,
        host=host,
        auto_open=not no_open,
        slm_url=slm_url,
    )


# ── tree ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.argument("graph_file", type=click.Path(exists=True, dir_okay=False))
def tree(graph_file: str) -> None:
    """Show the directory tree from the memory graph."""
    mg = load_graph(graph_file)
    g = mg.graph

    # Find root nodes (no incoming CONTAINS edges)
    roots = []
    for nid, attrs in g.nodes(data=True):
        if attrs.get("kind") == NodeKind.DIRECTORY.value:
            has_parent = any(
                g.edges[u, nid].get("kind") == "contains"
                for u in g.predecessors(nid)
            )
            if not has_parent:
                roots.append(nid)

    if not roots:
        console.print("[dim]No directory structure found.[/]")
        return

    def _add_children(parent_tree: Tree, parent_id: str) -> None:
        children = []
        for _, child, edata in g.out_edges(parent_id, data=True):
            if edata.get("kind") == "contains":
                children.append((child, g.nodes[child]))
        # Sort: dirs first, then files
        children.sort(key=lambda x: (x[1].get("kind") != "directory", x[1].get("path", "")))
        for cid, cattrs in children:
            kind = cattrs.get("kind", "")
            label = cattrs.get("path", cid).split("/")[-1] if "/" in cattrs.get("path", "") else cattrs.get("path", cid)
            icon = "📁" if kind == "directory" else "📄"
            lang = f" [{cattrs.get('language', '')}]" if cattrs.get("language") else ""
            branch = parent_tree.add(f"{icon} {label}{lang}")
            if kind == "directory":
                _add_children(branch, cid)

    for root_id in roots:
        root_attrs = g.nodes[root_id]
        t = Tree(f"📁 {root_attrs.get('path', root_id)}")
        _add_children(t, root_id)
        console.print(t)


if __name__ == "__main__":
    cli()
