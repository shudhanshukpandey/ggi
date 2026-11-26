"""
Serialisation: save and load MemoryGraphs as JSON or YAML files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ggi.graph import MemoryGraph


def _default_serialiser(obj: Any) -> Any:
    """Handle non-JSON-native types."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def save_graph(
    graph: MemoryGraph,
    path: str | Path,
    fmt: str = "json",
    indent: int = 2,
) -> Path:
    """
    Persist a MemoryGraph to disk.

    Parameters
    ----------
    graph : MemoryGraph
    path : str | Path
        Output file path.
    fmt : ``"json"`` or ``"yaml"``
    indent : int
        Indentation for pretty-printing.

    Returns
    -------
    Path
        The resolved output path.
    """
    path = Path(path)
    data = graph.to_dict()

    if fmt == "yaml":
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("Install PyYAML to use YAML format: pip install pyyaml") from exc
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=_default_serialiser, ensure_ascii=False)

    return path.resolve()


def load_graph(path: str | Path) -> MemoryGraph:
    """
    Load a MemoryGraph from a JSON or YAML file.

    The format is auto-detected from the file extension.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("Install PyYAML to use YAML format: pip install pyyaml") from exc
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    return MemoryGraph.from_dict(data)
