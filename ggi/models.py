"""
Core data models for the memory graph.

Every node and edge in the graph is a plain dataclass — easy to serialise,
easy to extend, zero magic.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ── Node kinds ───────────────────────────────────────────────────────────────

class NodeKind(str, Enum):
    """What a node represents in the memory graph."""

    FILE = "file"
    DIRECTORY = "directory"
    MODULE = "module"            # logical grouping (package, namespace)
    FUNCTION = "function"
    CLASS = "class"
    CONCEPT = "concept"          # abstract idea / domain concept
    CHANGE = "change"            # a recorded change / correction / implementation
    AGENT = "agent"              # an AI agent or human contributor
    ANNOTATION = "annotation"    # free-form note attached to anything


class EdgeKind(str, Enum):
    """Relationship between two nodes."""

    CONTAINS = "contains"            # directory → file, file → class, etc.
    IMPORTS = "imports"              # file A imports file B
    CALLS = "calls"                  # function A calls function B
    IMPLEMENTS = "implements"        # change node → what it implemented
    CORRECTS = "corrects"            # change node → what it fixed
    DEPENDS_ON = "depends_on"       # generic dependency
    RELATED_TO = "related_to"       # soft conceptual link
    ANNOTATED_BY = "annotated_by"   # node ← annotation
    AUTHORED_BY = "authored_by"     # change ← agent


# ── Node models ──────────────────────────────────────────────────────────────

@dataclass
class FileNode:
    """
    Represents a file (or directory / module) in the codebase.

    Attributes:
        id:          Stable unique identifier.
        path:        Relative path from project root.
        kind:        What this node represents.
        language:    Detected programming language (if applicable).
        summary:     One-line human summary of purpose.
        context:     Rich description of what this file does / contains.
        metadata:    Arbitrary key-value bag for extensions.
        content_hash: SHA-256 of file contents at scan time.
        created_at:  When this node was first created.
        updated_at:  Last time this node was refreshed.
    """

    path: str
    kind: NodeKind = NodeKind.FILE
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    language: str | None = None
    summary: str = ""
    context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def hash_file(filepath: str | Path) -> str:
        """Return the SHA-256 hex digest of a file's contents."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "kind": self.kind.value,
            "language": self.language,
            "summary": self.summary,
            "context": self.context,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileNode":
        data = dict(data)
        data["kind"] = NodeKind(data["kind"])
        return cls(**data)


@dataclass
class ChangeRecord:
    """
    A discrete change event: something implemented, corrected, or refactored.

    This is stored as a node of kind ``CHANGE`` and linked to the files
    or concepts it touches via edges.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    change_type: str = "implementation"  # implementation | correction | refactor | …
    targets: list[str] = field(default_factory=list)      # node IDs affected
    diff_summary: str = ""
    author: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "change_type": self.change_type,
            "targets": self.targets,
            "diff_summary": self.diff_summary,
            "author": self.author,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChangeRecord":
        return cls(**data)


@dataclass
class ContextEdge:
    """
    A directed edge between two nodes in the memory graph.

    ``source`` → ``target`` with a ``kind`` and an optional ``label``
    for human-readable context.
    """

    source: str          # node ID
    target: str          # node ID
    kind: EdgeKind = EdgeKind.RELATED_TO
    label: str = ""
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind.value,
            "label": self.label,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextEdge":
        data = dict(data)
        data["kind"] = EdgeKind(data["kind"])
        return cls(**data)
