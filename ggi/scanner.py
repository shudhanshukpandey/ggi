"""
Automatic codebase scanner.

Walks a directory tree, detects file languages, and builds a MemoryGraph
with directory-containment edges.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ggi.graph import MemoryGraph
from ggi.models import ContextEdge, EdgeKind, FileNode, NodeKind

# ── Language detection by extension ──────────────────────────────────────────

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".m": "objective-c",
    ".mm": "objective-cpp",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".txt": "text",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "config",
    ".dockerfile": "dockerfile",
    ".tf": "terraform",
    ".hcl": "hcl",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".lua": "lua",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".v": "verilog",
    ".sv": "systemverilog",
    ".vhd": "vhdl",
    ".zig": "zig",
    ".nim": "nim",
    ".jl": "julia",
    ".pl": "perl",
    ".pm": "perl",
}

# Directories / files that are always skipped
DEFAULT_IGNORE: set[str] = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
    ".DS_Store",
    "Thumbs.db",
}


def _detect_language(path: Path) -> str | None:
    """Detect language from file extension."""
    # Handle Dockerfile / Makefile style (no extension)
    name = path.name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    if name == "cmakelists.txt":
        return "cmake"
    return EXTENSION_MAP.get(path.suffix.lower())


def _should_ignore(name: str, extra_ignore: set[str] | None = None) -> bool:
    """Check if a file/dir name should be skipped."""
    ignore = DEFAULT_IGNORE | (extra_ignore or set())
    if name in ignore:
        return True
    # Glob-style check for *.egg-info etc.
    for pattern in ignore:
        if pattern.startswith("*") and name.endswith(pattern[1:]):
            return True
    return False


def _read_head(path: Path, max_bytes: int = 4096) -> str:
    """Read the first ``max_bytes`` of a file, ignoring binary files."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except (OSError, UnicodeDecodeError):
        return ""


def scan_directory(
    root: str | Path,
    *,
    project_name: str | None = None,
    max_depth: int | None = None,
    extra_ignore: set[str] | None = None,
    include_content_hash: bool = True,
    read_head_bytes: int = 2048,
) -> MemoryGraph:
    """
    Walk a directory and produce a MemoryGraph with one node per file/directory
    and ``CONTAINS`` edges forming the tree structure.

    Parameters
    ----------
    root : path
        Root directory to scan.
    project_name : str, optional
        Name to assign to the graph (defaults to the directory name).
    max_depth : int, optional
        Maximum recursion depth (``None`` = unlimited).
    extra_ignore : set[str], optional
        Additional names to skip.
    include_content_hash : bool
        Compute SHA-256 for each file (slower but enables change detection).
    read_head_bytes : int
        How many bytes of each file to include in context.

    Returns
    -------
    MemoryGraph
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"{root} is not a directory")

    name = project_name or root.name
    mg = MemoryGraph(project=name, description=f"Auto-scanned from {root}")

    # Maps absolute path → node ID
    path_to_id: dict[Path, str] = {}

    # Add root directory
    root_node = FileNode(
        path=".",
        kind=NodeKind.DIRECTORY,
        summary=f"Project root: {name}",
    )
    mg.add_file(root_node)
    path_to_id[root] = root_node.id

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        rel_depth = len(dirpath.relative_to(root).parts)
        if max_depth is not None and rel_depth >= max_depth:
            dirnames.clear()
            # Still process files in this directory, but don't recurse deeper
            # Fall through to handle files at this level

        # Filter ignored dirs (mutate in-place to prune os.walk)
        dirnames[:] = sorted(
            d for d in dirnames if not _should_ignore(d, extra_ignore)
        )

        parent_id = path_to_id.get(dirpath)

        # Subdirectories
        for dname in dirnames:
            dpath = dirpath / dname
            rel = str(dpath.relative_to(root))
            node = FileNode(
                path=rel,
                kind=NodeKind.DIRECTORY,
                summary=f"Directory: {rel}",
            )
            mg.add_file(node)
            path_to_id[dpath] = node.id
            if parent_id:
                mg.add_edge(ContextEdge(
                    source=parent_id,
                    target=node.id,
                    kind=EdgeKind.CONTAINS,
                    label=f"contains {dname}",
                ))

        # Files
        for fname in sorted(filenames):
            if _should_ignore(fname, extra_ignore):
                continue
            fpath = dirpath / fname
            rel = str(fpath.relative_to(root))
            lang = _detect_language(fpath)

            content_hash = None
            if include_content_hash:
                try:
                    content_hash = FileNode.hash_file(fpath)
                except OSError:
                    pass

            head = _read_head(fpath, read_head_bytes) if read_head_bytes > 0 else ""

            node = FileNode(
                path=rel,
                kind=NodeKind.FILE,
                language=lang,
                summary=f"{fname} ({lang or 'unknown'})",
                context=head[:read_head_bytes] if head else "",
                content_hash=content_hash,
            )
            mg.add_file(node)
            path_to_id[fpath] = node.id
            if parent_id:
                mg.add_edge(ContextEdge(
                    source=parent_id,
                    target=node.id,
                    kind=EdgeKind.CONTAINS,
                    label=f"contains {fname}",
                ))

    return mg
