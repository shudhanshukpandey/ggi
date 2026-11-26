"""
GraphQA — Graph-based Question Answering Engine for Codebase Memories.

Synthesises answers using graph topology, node summaries, implementation records,
correction history, annotations, and path analysis.
Optionally integrates with local SLMs (e.g. Ollama) or remote LLM endpoints.
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Any

from ggi.graph import MemoryGraph
from ggi.models import EdgeKind, NodeKind


class GraphQA:
    """
    Question-answering engine powered by a MemoryGraph.

    Uses graph traversal, change history, and context extraction to answer
    questions about architecture, implementations, bug fixes, and file relationships.
    Can also delegate synthesis to a local Small Language Model (SLM) via Ollama.
    """

    def __init__(
        self,
        graph: MemoryGraph,
        slm_url: str | None = None,
        slm_model: str = "llama3.2",
    ) -> None:
        self.graph = graph
        self.slm_url = slm_url  # e.g. "http://localhost:11434"
        self.slm_model = slm_model

    def ask(self, question: str) -> dict[str, Any]:
        """
        Answer a question using graph context and return cited nodes.
        """
        q = question.strip().lower()

        # 1. Did user ask about what was implemented?
        if any(w in q for w in ["implement", "feature", "added", "built", "created", "what was made"]):
            return self._answer_implementations(question)

        # 2. Did user ask about what was corrected / fixed / resolved / bugs?
        if any(w in q for w in ["correct", "fix", "bug", "error", "issue", "resolved", "problem", "fault"]):
            return self._answer_corrections(question)

        # 3. Did user ask about relationships or connections between two components?
        if any(w in q for w in ["connect", "call", "import", "depend", "communicate", "talk to", "flow", "relationship", "between"]):
            conn_ans = self._answer_connections(question)
            if conn_ans:
                return conn_ans

        # 4. Did user ask about a specific file or module?
        file_match = self._find_target_nodes(question)
        if file_match:
            return self._answer_node_context(question, file_match)

        # 5. Did user ask about authors, agents, contributors?
        if any(w in q for w in ["who", "author", "agent", "contributor", "wrote"]):
            return self._answer_authors(question)

        # 6. Did user ask for general architecture or summary?
        if any(w in q for w in ["structure", "architecture", "overview", "summary", "stats", "files", "components"]):
            return self._answer_overview(question)

        # 7. Fallback: semantic/keyword relevance search over all nodes & changes
        return self._answer_semantic_fallback(question)

    # ── Specialized Question Handlers ─────────────────────────────────────────

    def _answer_implementations(self, question: str) -> dict[str, Any]:
        changes = self.graph.find_nodes(kind=NodeKind.CHANGE)
        impls = [
            c for c in changes
            if c.get("change_type") != "correction"
        ]
        if not impls:
            return {
                "question": question,
                "answer": "No implementation records were found in this memory graph.",
                "cited_nodes": [],
            }

        lines = [f"Found **{len(impls)}** recorded implementation(s):\n"]
        cited: list[str] = []
        for i, ch in enumerate(impls, 1):
            title = ch.get("title", "Untitled implementation")
            desc = ch.get("description", "")
            targets = ch.get("targets", [])
            author = ch.get("author", "")
            cited.append(ch["id"])
            cited.extend(targets)

            target_names = []
            for tid in targets:
                tdata = self.graph.get_node(tid)
                if tdata:
                    target_names.append(tdata.get("path", tid))

            target_str = f" → targets: `{', '.join(target_names)}`" if target_names else ""
            author_str = f" *(by {author})*" if author else ""
            lines.append(f"{i}. **{title}**{author_str}{target_str}")
            if desc:
                lines.append(f"   > {desc}\n")

        answer = "\n".join(lines)
        if self.slm_url:
            answer = self._query_slm(question, answer)

        return {
            "question": question,
            "answer": answer,
            "cited_nodes": list(dict.fromkeys(cited)),
        }

    def _answer_corrections(self, question: str) -> dict[str, Any]:
        changes = self.graph.find_nodes(kind=NodeKind.CHANGE)
        corrections = [
            c for c in changes
            if c.get("change_type") == "correction" or "fix" in c.get("title", "").lower()
        ]
        if not corrections:
            return {
                "question": question,
                "answer": "No corrections or bug fixes were recorded in this memory graph.",
                "cited_nodes": [],
            }

        lines = [f"Found **{len(corrections)}** correction / bug fix record(s):\n"]
        cited: list[str] = []
        for i, ch in enumerate(corrections, 1):
            title = ch.get("title", "Correction")
            desc = ch.get("description", "")
            targets = ch.get("targets", [])
            author = ch.get("author", "")
            cited.append(ch["id"])
            cited.extend(targets)

            target_names = []
            for tid in targets:
                tdata = self.graph.get_node(tid)
                if tdata:
                    target_names.append(tdata.get("path", tid))

            target_str = f" (affected `{', '.join(target_names)}`)" if target_names else ""
            lines.append(f"{i}. 🔧 **{title}**{target_str}")
            if desc:
                lines.append(f"   > {desc}\n")

        # Also inspect annotations for corrections
        annotations = self.graph.find_nodes(kind=NodeKind.ANNOTATION)
        if annotations:
            lines.append("\n**Related Annotations:**")
            for ann in annotations:
                cited.append(ann["id"])
                lines.append(f"- 📝 {ann.get('text', '')}")

        answer = "\n".join(lines)
        if self.slm_url:
            answer = self._query_slm(question, answer)

        return {
            "question": question,
            "answer": answer,
            "cited_nodes": list(dict.fromkeys(cited)),
        }

    def _answer_connections(self, question: str) -> dict[str, Any] | None:
        nodes = self._find_target_nodes(question, max_results=4)
        if len(nodes) >= 2:
            src, dst = nodes[0], nodes[1]
            path = self.graph.path_between(src["id"], dst["id"])
            cited = [src["id"], dst["id"]]

            if path:
                path_str = " ➔ ".join(
                    self.graph.get_node(nid).get("path", nid) if self.graph.get_node(nid) else nid
                    for nid in path
                )
                cited.extend(path)
                return {
                    "question": question,
                    "answer": f"Connection path between `{src.get('path', src['id'])}` and `{dst.get('path', dst['id'])}`:\n\n**{path_str}**",
                    "cited_nodes": list(dict.fromkeys(cited)),
                }

        # Check explicit CALLS or IMPORTS edges
        calls_edges = self.graph.get_edges(kind=EdgeKind.CALLS)
        if calls_edges:
            lines = ["Found the following communication/call relationship(s) in the graph:\n"]
            cited = []
            for e in calls_edges:
                u_node = self.graph.get_node(e["source"]) or {}
                v_node = self.graph.get_node(e["target"]) or {}
                cited.extend([e["source"], e["target"]])
                u_name = u_node.get("path", e["source"])
                v_name = v_node.get("path", e["target"])
                label = e.get("label", "calls")
                lines.append(f"- `{u_name}` ➔ **{label}** ➔ `{v_name}`")
            return {
                "question": question,
                "answer": "\n".join(lines),
                "cited_nodes": list(dict.fromkeys(cited)),
            }

        return None

    def _answer_node_context(self, question: str, matched_nodes: list[dict[str, Any]]) -> dict[str, Any]:
        node = matched_nodes[0]
        ctx = self.graph.context_for(node["id"], depth=2)
        cited = [node["id"]]

        lines = [f"### Context for `{node.get('path', node['id'])}`\n"]
        lines.append(f"- **Kind:** {node.get('kind', 'file')}")
        if node.get("language"):
            lines.append(f"- **Language:** {node.get('language')}")
        if node.get("summary"):
            lines.append(f"- **Summary:** {node.get('summary')}")

        if ctx.get("changes"):
            lines.append("\n**Associated Changes / History:**")
            for ch in ctx["changes"]:
                cited.append(ch["id"])
                icon = "🔧" if ch.get("change_type") == "correction" else "✨"
                lines.append(f"- {icon} **{ch.get('title', 'Change')}** ({ch.get('change_type', 'change')})")
                if ch.get("description"):
                    lines.append(f"  > {ch['description']}")

        if ctx.get("annotations"):
            lines.append("\n**Annotations:**")
            for ann in ctx["annotations"]:
                cited.append(ann["id"])
                lines.append(f"- 📝 {ann.get('text', '')}")

        if ctx.get("incoming") or ctx.get("outgoing"):
            lines.append("\n**Dependencies / Relations:**")
            for inc in ctx.get("incoming", []):
                cited.append(inc["id"])
                lines.append(f"- ← {inc.get('edge_kind', 'related')} from `{inc.get('path', inc['id'])}`")
            for out in ctx.get("outgoing", []):
                cited.append(out["id"])
                lines.append(f"- → {out.get('edge_kind', 'related')} to `{out.get('path', out['id'])}`")

        answer = "\n".join(lines)
        if self.slm_url:
            answer = self._query_slm(question, answer)

        return {
            "question": question,
            "answer": answer,
            "cited_nodes": list(dict.fromkeys(cited)),
        }

    def _answer_authors(self, question: str) -> dict[str, Any]:
        agents = self.graph.find_nodes(kind=NodeKind.AGENT)
        changes = self.graph.find_nodes(kind=NodeKind.CHANGE)
        cited = [a["id"] for a in agents]

        lines = ["### Contributors & Authors\n"]
        for a in agents:
            name = a.get("name", a.get("id"))
            auth_changes = [c for c in changes if c.get("author") == name]
            lines.append(f"- **{name}** (authored {len(auth_changes)} change(s))")
            for ch in auth_changes:
                cited.append(ch["id"])
                lines.append(f"  - `{ch.get('title')}` [{ch.get('change_type')}]")

        return {
            "question": question,
            "answer": "\n".join(lines),
            "cited_nodes": list(dict.fromkeys(cited)),
        }

    def _answer_overview(self, question: str) -> dict[str, Any]:
        stats = self.graph.stats()
        lines = [
            f"### Memory Graph Overview: **{stats['project']}**\n",
            f"- **Total Nodes:** {stats['total_nodes']}",
            f"- **Total Edges:** {stats['total_edges']}",
            f"- **Components:** {stats['components']}\n",
            "**Node Breakdown:**",
        ]
        for k, v in sorted(stats["node_kinds"].items()):
            lines.append(f"- `{k}`: {v}")

        if stats["edge_kinds"]:
            lines.append("\n**Edge Breakdown:**")
            for k, v in sorted(stats["edge_kinds"].items()):
                lines.append(f"- `{k}`: {v}")

        all_nodes = [n["id"] for n in self.graph.find_nodes()]
        return {
            "question": question,
            "answer": "\n".join(lines),
            "cited_nodes": all_nodes[:10],
        }

    def _answer_semantic_fallback(self, question: str) -> dict[str, Any]:
        keywords = [w for w in re.findall(r"\w+", question.lower()) if len(w) > 2]
        scored_nodes = []

        for nid, attrs in self.graph.graph.nodes(data=True):
            score = 0
            text_corpus = " ".join([
                str(attrs.get("path", "")),
                str(attrs.get("title", "")),
                str(attrs.get("summary", "")),
                str(attrs.get("context", "")),
                str(attrs.get("description", "")),
                str(attrs.get("language", "")),
                str(attrs.get("kind", "")),
            ]).lower()

            for kw in keywords:
                if kw in text_corpus:
                    score += 1
            if score > 0:
                scored_nodes.append((score, nid, attrs))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        top = scored_nodes[:5]

        if not top:
            return {
                "question": question,
                "answer": f"I couldn't find specific nodes or change records matching '{question}'. Try asking about implementations, corrections, specific file names, or architecture.",
                "cited_nodes": [],
            }

        cited = [nid for _, nid, _ in top]
        lines = [f"Based on the codebase memory graph, here are the most relevant items for *\"{question}\"*:\n"]
        for _, nid, attrs in top:
            label = attrs.get("path", attrs.get("title", nid))
            kind = attrs.get("kind", "item")
            summary = attrs.get("summary", attrs.get("description", ""))
            lines.append(f"- **{label}** (`{kind}`)")
            if summary:
                lines.append(f"  > {summary}")

        answer = "\n".join(lines)
        if self.slm_url:
            answer = self._query_slm(question, answer)

        return {
            "question": question,
            "answer": answer,
            "cited_nodes": cited,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_target_nodes(self, text: str, max_results: int = 3) -> list[dict[str, Any]]:
        text_lower = text.lower()
        matches = []
        for nid, attrs in self.graph.graph.nodes(data=True):
            path = attrs.get("path", "").lower()
            name = path.split("/")[-1] if "/" in path else path
            title = attrs.get("title", "").lower()
            if (name and name in text_lower) or (title and title in text_lower):
                matches.append({"id": nid, **attrs})
        return matches[:max_results]

    def _query_slm(self, question: str, retrieved_context: str) -> str:
        """Call a local SLM via Ollama endpoint if configured."""
        if not self.slm_url:
            return retrieved_context

        endpoint = f"{self.slm_url.rstrip('/')}/api/generate"
        prompt = (
            f"You are an AI code intelligence assistant answering questions using a codebase memory graph.\n\n"
            f"Retrieved Graph Context:\n{retrieved_context}\n\n"
            f"User Question: {question}\n\n"
            f"Answer concisely, highlighting key files and changes directly citing the context."
        )
        payload = json.dumps({
            "model": self.slm_model,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", retrieved_context)
        except Exception:
            return retrieved_context
