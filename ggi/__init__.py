"""
GGI — Graph-based General Intelligence Memory

Build, query, and share rich context graphs of your codebase
so that any AI agent or human can understand what exists, what was built,
what was fixed, and how everything connects.
"""

__version__ = "0.1.0"

from ggi.graph import MemoryGraph
from ggi.models import FileNode, ChangeRecord, ContextEdge, NodeKind, EdgeKind
from ggi.scanner import scan_directory
from ggi.serializer import save_graph, load_graph

__all__ = [
    "MemoryGraph",
    "FileNode",
    "ChangeRecord",
    "ContextEdge",
    "NodeKind",
    "EdgeKind",
    "scan_directory",
    "save_graph",
    "load_graph",
]
