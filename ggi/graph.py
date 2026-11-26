"""
MemoryGraph — the central data structure.

A thin wrapper around ``networkx.DiGraph`` that knows about
FileNodes, ChangeRecords, and ContextEdges.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

import networkx as nx

from ggi.models import (
    ChangeRecord,
    ContextEdge,
    EdgeKind,
    FileNode,
    NodeKind,
)


class MemoryGraph:
    """
    An in-memory directed graph that tracks codebase structure, context,
    implementation history, and corrections.

    Usage::

        from ggi import MemoryGraph, FileNode, ChangeRecord

        g = MemoryGraph(project="my-app")
        node = g.add_file(FileNode(path="src/main.py", summary="Entry point"))
        g.record_change(ChangeRecord(
            title="Add CLI",
            change_type="implementation",
            targets=[node.id],
        ))
        g.summary()
    """

    def __init__(
        self,
        project: str = "untitled",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.project = project
        self.description = description
        self.metadata: dict[str, Any] = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._g = nx.DiGraph()

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def graph(self) -> nx.DiGraph:
        """Access the underlying NetworkX DiGraph."""
        return self._g

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    # ── Node operations ──────────────────────────────────────────────────

    def add_file(self, node: FileNode) -> FileNode:
        """Add a file / directory / module node to the graph."""
        self._g.add_node(node.id, **node.to_dict())
        return node

    def add_node_raw(
        self,
        node_id: str,
        kind: NodeKind,
        **attrs: Any,
    ) -> str:
        """Add an arbitrary node (concept, agent, annotation, …)."""
        self._g.add_node(node_id, kind=kind.value, **attrs)
        return node_id

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Return node attributes or ``None`` if not found."""
        if node_id in self._g:
            return dict(self._g.nodes[node_id])
        return None

    def find_nodes(
        self,
        kind: NodeKind | None = None,
        path_contains: str | None = None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query nodes by kind, path substring, or language."""
        results = []
        for nid, attrs in self._g.nodes(data=True):
            if kind and attrs.get("kind") != kind.value:
                continue
            if path_contains and path_contains not in attrs.get("path", ""):
                continue
            if language and attrs.get("language") != language:
                continue
            results.append({"id": nid, **attrs})
        return results

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its incident edges."""
        self._g.remove_node(node_id)

    # ── Edge operations ──────────────────────────────────────────────────

    def add_edge(self, edge: ContextEdge) -> None:
        """Add a directed contextual edge between two existing nodes."""
        self._g.add_edge(
            edge.source,
            edge.target,
            **edge.to_dict(),
        )

    def add_edge_simple(
        self,
        source: str,
        target: str,
        kind: EdgeKind = EdgeKind.RELATED_TO,
        label: str = "",
    ) -> None:
        """Convenience shorthand for adding an edge without constructing a dataclass."""
        self.add_edge(ContextEdge(source=source, target=target, kind=kind, label=label))

    def get_edges(
        self,
        node_id: str | None = None,
        kind: EdgeKind | None = None,
    ) -> list[dict[str, Any]]:
        """Return edges, optionally filtered by incident node or kind."""
        results = []
        edges: Iterator
        if node_id:
            edges = self._g.edges(node_id, data=True)
        else:
            edges = self._g.edges(data=True)
        for u, v, attrs in edges:
            if kind and attrs.get("kind") != kind.value:
                continue
            results.append({"source": u, "target": v, **attrs})
        return results

    # ── Change tracking ──────────────────────────────────────────────────

    def record_change(
        self,
        change: ChangeRecord,
        edge_kind: EdgeKind | None = None,
    ) -> ChangeRecord:
        """
        Record an implementation or correction.

        Creates a ``CHANGE`` node and links it to every target node with the
        appropriate edge kind (defaults to ``IMPLEMENTS`` for implementations,
        ``CORRECTS`` for corrections).
        """
        self._g.add_node(change.id, kind=NodeKind.CHANGE.value, **change.to_dict())

        inferred_kind = edge_kind
        if inferred_kind is None:
            if change.change_type == "correction":
                inferred_kind = EdgeKind.CORRECTS
            else:
                inferred_kind = EdgeKind.IMPLEMENTS

        for target_id in change.targets:
            if target_id in self._g:
                self.add_edge(
                    ContextEdge(
                        source=change.id,
                        target=target_id,
                        kind=inferred_kind,
                        label=change.title,
                    )
                )

        # Link author if present
        if change.author:
            author_id = f"agent:{change.author}"
            if author_id not in self._g:
                self.add_node_raw(author_id, NodeKind.AGENT, name=change.author)
            self.add_edge(
                ContextEdge(
                    source=change.id,
                    target=author_id,
                    kind=EdgeKind.AUTHORED_BY,
                    label=f"by {change.author}",
                )
            )

        return change

    # ── Annotate ─────────────────────────────────────────────────────────

    def annotate(self, node_id: str, note: str, author: str = "") -> str:
        """Attach a free-form annotation to any node."""
        import uuid

        ann_id = f"ann:{uuid.uuid4().hex[:8]}"
        self._g.add_node(
            ann_id,
            kind=NodeKind.ANNOTATION.value,
            text=note,
            author=author,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.add_edge(
            ContextEdge(
                source=node_id,
                target=ann_id,
                kind=EdgeKind.ANNOTATED_BY,
                label="annotation",
            )
        )
        return ann_id

    # ── Traversal helpers ────────────────────────────────────────────────

    def neighbours(self, node_id: str, depth: int = 1) -> dict[str, Any]:
        """
        Return the ego-graph (neighbourhood) of a node up to ``depth`` hops.
        """
        ego = nx.ego_graph(self._g, node_id, radius=depth)
        return {
            "center": node_id,
            "nodes": [
                {"id": n, **ego.nodes[n]} for n in ego.nodes
            ],
            "edges": [
                {"source": u, "target": v, **d}
                for u, v, d in ego.edges(data=True)
            ],
        }

    def path_between(self, source: str, target: str) -> list[str] | None:
        """Return shortest path between two nodes, or ``None``."""
        try:
            return nx.shortest_path(self._g, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def connected_components(self) -> list[set[str]]:
        """Return weakly connected components."""
        return [
            comp for comp in nx.weakly_connected_components(self._g)
        ]

    # ── Context extraction (for agents) ──────────────────────────────────

    def context_for(self, node_id: str, depth: int = 2) -> dict[str, Any]:
        """
        Build a rich context bundle for a node — designed to be handed to
        another AI agent so it can understand the node's role in the project.

        Returns a dict with:
        - ``node``: the node itself
        - ``changes``: all change records touching this node
        - ``annotations``: all annotations
        - ``neighbours``: nearby nodes up to ``depth`` hops
        - ``incoming``: what depends on / imports this node
        - ``outgoing``: what this node depends on / imports
        """
        node_data = self.get_node(node_id)
        if node_data is None:
            return {"error": f"Node '{node_id}' not found"}

        # Changes
        changes = []
        for pred in self._g.predecessors(node_id):
            pdata = self._g.nodes[pred]
            if pdata.get("kind") == NodeKind.CHANGE.value:
                changes.append({"id": pred, **pdata})

        # Annotations
        annotations = []
        for _, succ, edata in self._g.edges(node_id, data=True):
            if edata.get("kind") == EdgeKind.ANNOTATED_BY.value:
                annotations.append({"id": succ, **self._g.nodes[succ]})

        # Incoming / outgoing
        incoming = [
            {"id": u, "edge_kind": d.get("kind"), **self._g.nodes[u]}
            for u, _, d in self._g.in_edges(node_id, data=True)
        ]
        outgoing = [
            {"id": v, "edge_kind": d.get("kind"), **self._g.nodes[v]}
            for _, v, d in self._g.out_edges(node_id, data=True)
        ]

        return {
            "node": {"id": node_id, **node_data},
            "changes": changes,
            "annotations": annotations,
            "incoming": incoming,
            "outgoing": outgoing,
            "neighbours": self.neighbours(node_id, depth=depth),
        }

    # ── Stats / summary ──────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return high-level statistics about the graph."""
        kinds: dict[str, int] = {}
        for _, attrs in self._g.nodes(data=True):
            k = attrs.get("kind", "unknown")
            kinds[k] = kinds.get(k, 0) + 1

        edge_kinds: dict[str, int] = {}
        for _, _, attrs in self._g.edges(data=True):
            k = attrs.get("kind", "unknown")
            edge_kinds[k] = edge_kinds.get(k, 0) + 1

        return {
            "project": self.project,
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "node_kinds": kinds,
            "edge_kinds": edge_kinds,
            "components": len(self.connected_components()),
        }

    def summary(self) -> str:
        """Pretty one-line summary string."""
        s = self.stats()
        return (
            f"MemoryGraph '{s['project']}': "
            f"{s['total_nodes']} nodes, {s['total_edges']} edges, "
            f"{s['components']} component(s)"
        )

    def __repr__(self) -> str:
        return f"<MemoryGraph project={self.project!r} nodes={self.node_count} edges={self.edge_count}>"

    # ── Serialisation hooks ──────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire graph to a plain dict."""
        return {
            "project": self.project,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "nodes": [
                {"id": nid, **attrs}
                for nid, attrs in self._g.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, **d}
                for u, v, d in self._g.edges(data=True)
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryGraph":
        """Reconstruct a MemoryGraph from a serialised dict."""
        mg = cls(
            project=data.get("project", "untitled"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )
        mg.created_at = data.get("created_at", mg.created_at)
        for node in data.get("nodes", []):
            node = dict(node)
            nid = node.pop("id")
            mg._g.add_node(nid, **node)
        for edge in data.get("edges", []):
            edge = dict(edge)
            src = edge.pop("source")
            tgt = edge.pop("target")
            mg._g.add_edge(src, tgt, **edge)
        return mg
