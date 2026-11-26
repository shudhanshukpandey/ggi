"""Tests for GGI core graph and models."""

import json
import tempfile
from pathlib import Path

import pytest

from ggi import MemoryGraph, FileNode, ChangeRecord, ContextEdge, NodeKind, EdgeKind
from ggi.serializer import save_graph, load_graph
from ggi.scanner import scan_directory


# ── Model tests ──────────────────────────────────────────────────────────────


class TestFileNode:
    def test_create(self):
        node = FileNode(path="src/main.py", language="python", summary="Entry point")
        assert node.path == "src/main.py"
        assert node.kind == NodeKind.FILE
        assert node.language == "python"
        assert node.id  # auto-generated

    def test_to_dict_roundtrip(self):
        node = FileNode(path="lib/utils.ts", kind=NodeKind.MODULE, language="typescript")
        d = node.to_dict()
        restored = FileNode.from_dict(d)
        assert restored.path == node.path
        assert restored.kind == node.kind
        assert restored.language == node.language

    def test_hash_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world")
        h = FileNode.hash_file(f)
        assert len(h) == 64  # SHA-256 hex


class TestChangeRecord:
    def test_create(self):
        cr = ChangeRecord(
            title="Fix login bug",
            change_type="correction",
            author="alice",
        )
        assert cr.change_type == "correction"
        assert cr.author == "alice"

    def test_to_dict_roundtrip(self):
        cr = ChangeRecord(title="Add feature X", targets=["abc123"])
        d = cr.to_dict()
        restored = ChangeRecord.from_dict(d)
        assert restored.title == cr.title
        assert restored.targets == ["abc123"]


class TestContextEdge:
    def test_create(self):
        edge = ContextEdge(source="a", target="b", kind=EdgeKind.IMPORTS)
        assert edge.source == "a"
        assert edge.kind == EdgeKind.IMPORTS

    def test_roundtrip(self):
        edge = ContextEdge(source="x", target="y", kind=EdgeKind.CORRECTS, label="fixed it")
        d = edge.to_dict()
        restored = ContextEdge.from_dict(d)
        assert restored.kind == EdgeKind.CORRECTS
        assert restored.label == "fixed it"


# ── Graph tests ──────────────────────────────────────────────────────────────


class TestMemoryGraph:
    def test_add_and_query_nodes(self):
        mg = MemoryGraph(project="test")
        n1 = mg.add_file(FileNode(path="a.py", language="python"))
        n2 = mg.add_file(FileNode(path="b.js", language="javascript"))
        assert mg.node_count == 2

        results = mg.find_nodes(language="python")
        assert len(results) == 1
        assert results[0]["path"] == "a.py"

    def test_add_edges(self):
        mg = MemoryGraph(project="test")
        n1 = mg.add_file(FileNode(path="a.py", id="a"))
        n2 = mg.add_file(FileNode(path="b.py", id="b"))
        mg.add_edge(ContextEdge(source="a", target="b", kind=EdgeKind.IMPORTS))
        assert mg.edge_count == 1

        edges = mg.get_edges(node_id="a")
        assert len(edges) == 1
        assert edges[0]["kind"] == "imports"

    def test_record_change_implementation(self):
        mg = MemoryGraph(project="test")
        n = mg.add_file(FileNode(path="app.py", id="app"))
        cr = mg.record_change(ChangeRecord(
            title="Build the CLI",
            change_type="implementation",
            targets=["app"],
            author="bob",
        ))
        # Should have: file node + change node + agent node
        assert mg.node_count == 3
        # Edges: change→app (implements), change→agent (authored_by)
        assert mg.edge_count == 2

    def test_record_change_correction(self):
        mg = MemoryGraph(project="test")
        n = mg.add_file(FileNode(path="app.py", id="app"))
        cr = mg.record_change(ChangeRecord(
            title="Fix crash on empty input",
            change_type="correction",
            targets=["app"],
        ))
        edges = mg.get_edges(kind=EdgeKind.CORRECTS)
        assert len(edges) == 1

    def test_annotate(self):
        mg = MemoryGraph(project="test")
        mg.add_file(FileNode(path="x.py", id="x"))
        ann_id = mg.annotate("x", "This module needs refactoring", author="alice")
        assert ann_id.startswith("ann:")
        assert mg.node_count == 2  # file + annotation

    def test_context_for(self):
        mg = MemoryGraph(project="test")
        mg.add_file(FileNode(path="main.py", id="main", summary="Entry point"))
        mg.record_change(ChangeRecord(
            title="Initial implementation",
            targets=["main"],
        ))
        mg.annotate("main", "Core module")

        ctx = mg.context_for("main")
        assert ctx["node"]["path"] == "main.py"
        assert len(ctx["changes"]) == 1
        assert len(ctx["annotations"]) == 1

    def test_context_for_missing(self):
        mg = MemoryGraph(project="test")
        ctx = mg.context_for("nonexistent")
        assert "error" in ctx

    def test_neighbours(self):
        mg = MemoryGraph(project="test")
        mg.add_file(FileNode(path="a.py", id="a"))
        mg.add_file(FileNode(path="b.py", id="b"))
        mg.add_file(FileNode(path="c.py", id="c"))
        mg.add_edge_simple("a", "b", EdgeKind.IMPORTS)
        mg.add_edge_simple("b", "c", EdgeKind.IMPORTS)

        n = mg.neighbours("a", depth=1)
        assert len(n["nodes"]) == 2  # a + b

    def test_path_between(self):
        mg = MemoryGraph(project="test")
        mg.add_file(FileNode(path="a.py", id="a"))
        mg.add_file(FileNode(path="b.py", id="b"))
        mg.add_file(FileNode(path="c.py", id="c"))
        mg.add_edge_simple("a", "b")
        mg.add_edge_simple("b", "c")

        path = mg.path_between("a", "c")
        assert path == ["a", "b", "c"]
        assert mg.path_between("c", "a") is None  # directed

    def test_stats(self):
        mg = MemoryGraph(project="test")
        mg.add_file(FileNode(path="a.py"))
        mg.add_file(FileNode(path="b.py"))
        s = mg.stats()
        assert s["total_nodes"] == 2
        assert s["project"] == "test"

    def test_summary(self):
        mg = MemoryGraph(project="demo")
        assert "demo" in mg.summary()
        assert "0 nodes" in mg.summary()


# ── Serialisation tests ──────────────────────────────────────────────────────


class TestSerialisation:
    def test_json_roundtrip(self, tmp_path):
        mg = MemoryGraph(project="serial-test")
        mg.add_file(FileNode(path="x.py", id="x", language="python"))
        mg.add_file(FileNode(path="y.py", id="y", language="python"))
        mg.add_edge_simple("x", "y", EdgeKind.IMPORTS)
        mg.record_change(ChangeRecord(
            title="Add imports",
            targets=["x"],
            author="test",
        ))

        out = save_graph(mg, tmp_path / "g.json")
        loaded = load_graph(out)
        assert loaded.project == "serial-test"
        assert loaded.node_count == mg.node_count
        assert loaded.edge_count == mg.edge_count

    def test_yaml_roundtrip(self, tmp_path):
        mg = MemoryGraph(project="yaml-test")
        mg.add_file(FileNode(path="a.rs", id="a"))

        out = save_graph(mg, tmp_path / "g.yaml", fmt="yaml")
        loaded = load_graph(out)
        assert loaded.project == "yaml-test"
        assert loaded.node_count == 1


# ── Scanner tests ────────────────────────────────────────────────────────────


class TestScanner:
    def test_scan_simple(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "src" / "utils.py").write_text("def add(a, b): return a + b")
        (tmp_path / "README.md").write_text("# My Project")

        mg = scan_directory(tmp_path, project_name="test-scan")
        assert mg.project == "test-scan"
        # root dir + src dir + 3 files = 5 nodes
        assert mg.node_count == 5

        py_files = mg.find_nodes(language="python")
        assert len(py_files) == 2

    def test_scan_ignores_pycache(self, tmp_path):
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "mod.cpython-312.pyc").write_bytes(b"\x00")
        (tmp_path / "app.py").write_text("pass")

        mg = scan_directory(tmp_path)
        paths = [n.get("path", "") for n in mg.find_nodes()]
        assert not any("__pycache__" in p for p in paths)

    def test_scan_max_depth(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "a" / "b" / "c.py").write_text("deep")

        mg = scan_directory(tmp_path, max_depth=1)
        paths = [n.get("path", "") for n in mg.find_nodes()]
        assert not any("b" in p for p in paths)
