"""
Export the memory graph as an interactive HTML visualisation using pyvis,
as a comprehensive standalone interactive web app with Q&A panel (2D Fluid & 3D Galaxy views),
or as static DOT / Mermaid diagrams.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ggi.graph import MemoryGraph
from ggi.models import NodeKind


# ── Colour palette per node kind ─────────────────────────────────────────────

KIND_COLOURS: dict[str, str] = {
    NodeKind.FILE.value: "#38bdf8",         # Sky blue
    NodeKind.DIRECTORY.value: "#4ade80",    # Mint green
    NodeKind.MODULE.value: "#a3e635",       # Lime green
    NodeKind.FUNCTION.value: "#facc15",     # Amber yellow
    NodeKind.CLASS.value: "#fb923c",        # Warm orange
    NodeKind.CONCEPT.value: "#c084fc",      # Purple
    NodeKind.CHANGE.value: "#f43f5e",       # Rose red (actions/changes)
    NodeKind.AGENT.value: "#94a3b8",        # Slate gray
    NodeKind.ANNOTATION.value: "#fde047",   # Bright note yellow
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


def to_interactive_html(
    graph: MemoryGraph,
    output: str | Path = "interactive_graph.html",
    title: str | None = None,
) -> Path:
    """
    Generate a full-featured, standalone interactive web application containing:
    - 2D Fluid Dynamic Moving Graph with continuous physics & animated flowing pulses
    - 3D Galaxy View with orbital camera rotation, glowing nebulae, and particle streams
    - Node Details Inspector side panel
    - Integrated Question & Answer (Q&A) Panel powered by graph context intelligence
    - Graph-to-Q&A cross-linking (clicking cited nodes highlights them on canvas)
    """
    out_path = Path(output)
    graph_dict = graph.to_dict()
    # Safely escape HTML closing tags so scanned HTML files (e.g. index.html) don't break <script>
    graph_json = (
        json.dumps(graph_dict, default=str)
        .replace("</", r"<\/")
        .replace("<!--", r"<\!--")
    )
    proj_title = title or graph.project or "Codebase Memory Graph"

    base_lib = Path(__file__).resolve().parent.parent / "lib"
    vis_dir = base_lib / "vis-9.1.2"
    vis_js_file = vis_dir / "vis-network.min.js"
    vis_css_file = vis_dir / "vis-network.css"
    three_js_file = base_lib / "three.min.js"
    three_d_file = base_lib / "3d-force-graph.min.js"

    vis_script = f"<script>{vis_js_file.read_text(encoding='utf-8')}</script>" if vis_js_file.exists() else '<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>'
    vis_css = f"<style>{vis_css_file.read_text(encoding='utf-8')}</style>" if vis_css_file.exists() else ""
    three_script = f"<script>{three_js_file.read_text(encoding='utf-8')}</script>" if three_js_file.exists() else '<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>'
    three_d_script = f"<script>{three_d_file.read_text(encoding='utf-8')}</script>" if three_d_file.exists() else '<script src="https://unpkg.com/3d-force-graph"></script>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GGI — {proj_title}</title>
  {vis_css}
  {vis_script}
  {three_script}
  {three_d_script}
  <style>
    :root {{
      --bg: #070a13;
      --card-bg: rgba(15, 23, 42, 0.88);
      --border: rgba(255, 255, 255, 0.1);
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --change: #f43f5e;
      --file: #38bdf8;
      --dir: #4ade80;
      --agent: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }}

    /* Main Canvas Area */
    #main-container {{
      flex: 1;
      display: flex;
      flex-direction: column;
      position: relative;
      height: 100vh;
    }}

    /* Top Navbar */
    #navbar {{
      height: 56px;
      padding: 0 1.25rem;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      backdrop-filter: blur(12px);
      z-index: 10;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-weight: 700;
      font-size: 1.1rem;
    }}
    .brand .logo {{ font-size: 1.4rem; }}
    .brand span {{ background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}

    .toolbar {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .search-input {{
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.4rem 0.8rem;
      color: var(--text);
      font-size: 0.85rem;
      outline: none;
      width: 180px;
      transition: all 0.2s;
    }}
    .search-input:focus {{
      border-color: var(--accent);
      width: 240px;
    }}
    .btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 8px;
      padding: 0.4rem 0.75rem;
      font-size: 0.82rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s;
      user-select: none;
    }}
    .btn:hover {{ background: rgba(255, 255, 255, 0.15); }}
    .btn.active {{ background: var(--accent); color: #04101e; font-weight: 600; border-color: var(--accent); }}

    /* Canvas Containers */
    #network {{
      flex: 1;
      width: 100%;
      height: calc(100vh - 56px);
      outline: none;
      position: absolute;
      top: 56px;
      left: 0;
    }}
    #network-3d {{
      flex: 1;
      width: 100%;
      height: calc(100vh - 56px);
      outline: none;
      position: absolute;
      top: 56px;
      left: 0;
      display: none;
    }}

    /* Legend Overlay */
    .legend {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      font-size: 0.78rem;
      backdrop-filter: blur(8px);
      z-index: 5;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      user-select: none;
    }}
    .legend-color {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }}

    /* Motion Status Badge */
    .motion-indicator {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.74rem;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 0.2rem 0.5rem;
      border-radius: 12px;
      border: 1px solid rgba(56, 189, 248, 0.3);
    }}
    .pulse-dot {{
      width: 6px;
      height: 6px;
      background: #38bdf8;
      border-radius: 50%;
      animation: blink 1.2s infinite ease-in-out;
    }}
    @keyframes blink {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.3; transform: scale(0.7); }}
    }}

    /* Right Sidebar (Q&A and Inspector) */
    #sidebar {{
      width: 440px;
      height: 100vh;
      background: var(--card-bg);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      backdrop-filter: blur(16px);
      z-index: 20;
      transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease;
      position: relative;
    }}
    #sidebar.collapsed {{
      width: 0 !important;
      min-width: 0 !important;
      max-width: 0 !important;
      border-left: none !important;
      opacity: 0 !important;
      pointer-events: none !important;
      overflow: hidden !important;
      display: none !important;
    }}
    .tabs {{
      display: flex;
      border-bottom: 1px solid var(--border);
      background: rgba(0,0,0,0.2);
      align-items: center;
    }}
    .tab-btn {{
      flex: 1;
      padding: 0.8rem 0;
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
    }}
    .tab-btn.active {{
      color: var(--accent);
      border-bottom-color: var(--accent);
      background: rgba(56, 189, 248, 0.05);
    }}
    .btn-collapse-sidebar {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1rem;
      padding: 0.6rem 0.9rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      border-left: 1px solid var(--border);
      transition: color 0.2s, background 0.2s;
    }}
    .btn-collapse-sidebar:hover {{
      color: #fff;
      background: rgba(255, 255, 255, 0.08);
    }}

    .floating-sidebar-toggle {{
      position: absolute;
      top: 68px;
      right: 0;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-right: none;
      color: var(--accent);
      padding: 0.5rem 0.85rem;
      border-radius: 8px 0 0 8px;
      cursor: pointer;
      font-size: 0.84rem;
      font-weight: 600;
      display: none;
      align-items: center;
      gap: 0.4rem;
      box-shadow: -4px 0 16px rgba(0,0,0,0.5);
      z-index: 15;
      transition: all 0.2s ease;
      backdrop-filter: blur(12px);
    }}
    .floating-sidebar-toggle:hover {{
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--accent);
      color: #fff;
    }}
    .floating-sidebar-toggle.visible {{
      display: flex;
    }}

    .tab-content {{
      flex: 1;
      overflow-y: auto;
      display: none;
      flex-direction: column;
    }}
    .tab-content.active {{
      display: flex;
    }}

    /* Q&A Section */
    .qa-history {{
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .qa-msg {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      font-size: 0.88rem;
      line-height: 1.5;
    }}
    .qa-msg.user {{
      align-self: flex-end;
      background: #0284c7;
      color: #fff;
      padding: 0.6rem 0.9rem;
      border-radius: 12px 12px 2px 12px;
      max-width: 85%;
    }}
    .qa-msg.assistant {{
      align-self: flex-start;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border);
      padding: 0.8rem 1rem;
      border-radius: 12px 12px 12px 2px;
      max-width: 95%;
    }}
    .qa-msg pre {{
      background: rgba(0,0,0,0.4);
      padding: 0.5rem;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 0.8rem;
      color: #38bdf8;
    }}
    .qa-msg code {{
      background: rgba(0,0,0,0.3);
      padding: 0.1rem 0.3rem;
      border-radius: 4px;
      font-family: monospace;
      color: #7dd3fc;
    }}
    .cited-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: #38bdf8;
      border-radius: 6px;
      padding: 0.15rem 0.45rem;
      font-size: 0.75rem;
      cursor: pointer;
      margin: 0.15rem;
      transition: all 0.2s;
    }}
    .cited-badge:hover {{
      background: rgba(56, 189, 248, 0.3);
      transform: translateY(-1px);
    }}

    .qa-suggestions {{
      padding: 0.6rem 1rem;
      border-top: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      background: rgba(0,0,0,0.15);
    }}
    .pill {{
      font-size: 0.74rem;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 0.25rem 0.6rem;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s;
    }}
    .pill:hover {{
      color: var(--accent);
      border-color: var(--accent);
      background: rgba(56, 189, 248, 0.1);
    }}

    .qa-input-bar {{
      padding: 0.8rem 1rem;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 0.5rem;
      background: var(--card-bg);
    }}
    .qa-input {{
      flex: 1;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.6rem 0.8rem;
      color: var(--text);
      font-size: 0.88rem;
      outline: none;
    }}
    .qa-input:focus {{ border-color: var(--accent); }}
    .send-btn {{
      background: var(--accent);
      color: #04101e;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      padding: 0 1rem;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .send-btn:hover {{ background: var(--accent-hover); }}

    /* Node Inspector Section */
    .inspector {{
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1.2rem;
    }}
    .node-header {{
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }}
    .node-title {{
      font-size: 1.2rem;
      font-weight: 700;
      color: #fff;
      word-break: break-all;
    }}
    .node-kind-tag {{
      display: inline-block;
      align-self: flex-start;
      font-size: 0.72rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.05em;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      margin-top: 0.2rem;
    }}
    .meta-box {{
      background: rgba(0,0,0,0.3);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.8rem;
      font-size: 0.84rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}
    .meta-row {{
      display: flex;
      justify-content: space-between;
    }}
    .meta-label {{ color: var(--text-muted); }}
    .code-preview {{
      background: rgba(0,0,0,0.5);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.8rem;
      font-family: monospace;
      font-size: 0.78rem;
      color: #bae6fd;
      max-height: 200px;
      overflow-y: auto;
      white-space: pre-wrap;
    }}
    .section-title {{
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }}
    .card-list {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .change-card {{
      background: rgba(255,255,255,0.04);
      border: 1px solid var(--border);
      border-left: 3px solid var(--change);
      border-radius: 6px;
      padding: 0.6rem 0.8rem;
      font-size: 0.82rem;
    }}
    .empty-state {{
      text-align: center;
      color: var(--text-muted);
      padding: 3rem 1rem;
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>

  <!-- Main Canvas Section -->
  <div id="main-container">
    <div id="navbar">
      <div class="brand">
        <span class="logo">🧠</span>
        <span>GGI Memory Graph</span>
        <span class="motion-indicator"><span class="pulse-dot"></span> Live Motion</span>
        <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal; margin-left: 0.4rem;">{proj_title}</span>
      </div>

      <div class="toolbar">
        <input type="text" id="search-input" class="search-input" placeholder="Search node or file..." />
        <button id="btn-view-mode" class="btn">🌌 3D Galaxy</button>
        <button id="btn-motion" class="btn active">🌊 Float Motion</button>
        <button id="btn-pulses" class="btn active">✨ Flow Pulses</button>
        <button id="btn-labels" class="btn active">🏷️ Clean Labels</button>
        <button id="btn-spacing" class="btn">↔️ Spacing</button>
        <button id="btn-fit" class="btn">🎯 Center</button>
        <button id="btn-toggle-sidebar" class="btn active">▶ Collapse Panel</button>
      </div>
    </div>

    <!-- 2D Canvas -->
    <div id="network"></div>

    <!-- 3D Canvas -->
    <div id="network-3d"></div>

    <div class="legend">
      <div style="font-weight: 600; margin-bottom: 0.2rem; color: var(--text-muted);">Node Kinds</div>
      <div class="legend-item" onclick="filterByKind('file')"><span class="legend-color" style="background:#38bdf8;"></span> File</div>
      <div class="legend-item" onclick="filterByKind('directory')"><span class="legend-color" style="background:#4ade80;"></span> Directory</div>
      <div class="legend-item" onclick="filterByKind('change')"><span class="legend-color" style="background:#f43f5e;"></span> Change / Fix</div>
      <div class="legend-item" onclick="filterByKind('agent')"><span class="legend-color" style="background:#94a3b8;"></span> Agent</div>
      <div class="legend-item" onclick="filterByKind('annotation')"><span class="legend-color" style="background:#fde047;"></span> Annotation</div>
    </div>

    <!-- Floating Expand Button when Sidebar is collapsed -->
    <button id="floating-sidebar-toggle" class="floating-sidebar-toggle" onclick="toggleSidebar(true)" title="Expand Chat & Node Inspector">
      💬 Chat &amp; Inspector ◀
    </button>
  </div>

  <!-- Right Sidebar: Q&A & Node Inspector -->
  <div id="sidebar">
    <div class="tabs">
      <button class="tab-btn active" id="tab-qa-btn" onclick="switchTab('qa')">💬 Question & Answer</button>
      <button class="tab-btn" id="tab-inspector-btn" onclick="switchTab('inspector')">🔍 Node Inspector</button>
      <button class="btn-collapse-sidebar" id="btn-collapse-sidebar" title="Collapse Panel (Chat & Inspector)" onclick="toggleSidebar(false)">✕</button>
    </div>

    <!-- Q&A Tab -->
    <div class="tab-content active" id="tab-qa">
      <div class="qa-history" id="qa-history">
        <div class="qa-msg assistant">
          👋 Welcome to the <b>GGI Graph Question Panel</b>!
          <br><br>
          Ask any question about what was implemented, what was corrected, how files connect, or system architecture.
        </div>
      </div>

      <div class="qa-suggestions">
        <div class="pill" onclick="askPreset('What was implemented in this project?')">✨ What was implemented?</div>
        <div class="pill" onclick="askPreset('What bugs or errors were corrected?')">🔧 What was corrected?</div>
        <div class="pill" onclick="askPreset('How does React frontend connect to Django backend?')">🔄 React ➔ Django Flow</div>
        <div class="pill" onclick="askPreset('Give an overview of the codebase architecture.')">📊 Codebase Overview</div>
      </div>

      <div class="qa-input-bar">
        <input type="text" id="qa-input" class="qa-input" placeholder="Ask a question about the codebase..." onkeydown="handleKey(event)" />
        <button class="send-btn" onclick="submitQuestion()">Ask</button>
      </div>
    </div>

    <!-- Node Inspector Tab -->
    <div class="tab-content" id="tab-inspector">
      <div id="inspector-content" class="inspector">
        <div class="empty-state">
          👉 Click on any node in the graph to inspect its context, code preview, connected changes, and incoming/outgoing dependencies.
        </div>
      </div>
    </div>
  </div>

  <script>
    // Injected MemoryGraph payload
    const rawData = {graph_json};

    const KIND_COLORS = {{
      file: "#38bdf8",
      directory: "#4ade80",
      module: "#a3e635",
      function: "#facc15",
      class: "#fb923c",
      concept: "#c084fc",
      change: "#f43f5e",
      agent: "#94a3b8",
      annotation: "#fde047"
    }};

    const KIND_SHAPES = {{
      file: "dot",
      directory: "triangle",
      change: "triangleDown",
      agent: "box",
      annotation: "ellipse"
    }};

    // Format nodes for 2D vis.js with readable, non-overlapping names
    const nodes = new vis.DataSet(
      rawData.nodes.map(n => {{
        let label = n.title || n.name || n.id;
        if (n.path) {{
          const parts = n.path.split("/").filter(Boolean);
          if (n.kind === "directory") {{
            label = "📁 " + (parts[parts.length - 1] || n.id);
          }} else if (parts.length >= 2) {{
            label = parts.slice(-2).join("/");
          }} else {{
            label = parts[parts.length - 1] || n.id;
          }}
        }} else if (n.kind === "change") {{
          const prefix = n.change_type === "correction" ? "🔧 " : "✨ ";
          label = prefix + (n.title || n.id);
        }}
        const kind = n.kind || "file";
        const isChange = kind === "change";
        const baseColor = KIND_COLORS[kind] || "#94a3b8";

        return {{
          id: n.id,
          label: label,
          title: `<b>${{n.path || n.title || n.id}}</b><br>Kind: ${{kind}}`,
          color: {{
            background: baseColor,
            border: "#ffffff",
            highlight: {{ background: "#ffffff", border: baseColor }}
          }},
          shape: KIND_SHAPES[kind] || "dot",
          size: kind === "directory" ? 26 : (isChange ? 20 : 16),
          font: {{
            color: "#ffffff",
            size: kind === "directory" ? 17 : (isChange ? 14 : 14),
            face: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            strokeWidth: 0,
            background: "rgba(10, 15, 26, 0.9)",
            vadjust: 2
          }},
          raw: n,
          baseColor: baseColor
        }};
      }})
    );

    // Filter out redundant "contains" label clutter by default
    let edgeLabelMode = "clean"; // "clean" (semantic only) | "all" | "none"

    function getEdgeDisplayLabel(e) {{
      const isContainment = e.kind === "contains" || (e.label && e.label.startsWith("contains "));
      if (edgeLabelMode === "clean") {{
        return isContainment ? "" : (e.label || e.kind || "");
      }}
      if (edgeLabelMode === "none") return "";
      return e.label || e.kind || "";
    }}

    const edges = new vis.DataSet(
      rawData.edges.map(e => ({{
        id: `${{e.source}}->${{e.target}}`,
        from: e.source,
        to: e.target,
        label: getEdgeDisplayLabel(e),
        arrows: "to",
        color: {{ color: "rgba(148, 163, 184, 0.35)", highlight: "#38bdf8" }},
        font: {{
          color: "#94a3b8",
          size: 11,
          strokeWidth: 0,
          background: "rgba(10, 15, 26, 0.85)",
          align: "middle"
        }},
        smooth: false,
        raw: e
      }}))
    );

    // Initialise 2D Network with wide, overlap-free physics
    const container2d = document.getElementById("network");
    const options2d = {{
      nodes: {{
        borderWidth: 1.5,
        shadow: true
      }},
      edges: {{
        width: 1.5,
        shadow: true,
        smooth: false
      }},
      physics: {{
        solver: "forceAtlas2Based",
        forceAtlas2Based: {{
          gravitationalConstant: -180,
          centralGravity: 0.005,
          springLength: 220,
          springConstant: 0.05,
          damping: 0.28,
          avoidOverlap: 1.0
        }},
        maxVelocity: 30,
        minVelocity: 0.05,
        stabilization: {{
          enabled: true,
          iterations: 60,
          updateInterval: 10
        }}
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 100,
        zoomView: true
      }}
    }};

    const network2d = new vis.Network(container2d, {{ nodes, edges }}, options2d);

    // ── Continuous 2D Motion & Animated Edge Flow Pulses ───────────────────────
    let motionEnabled = true;
    let pulsesEnabled = true;
    let is3DMode = false;
    let graph3dInstance = null;

    // Keep 2D simulation continuously alive and floating
    let motionInterval = setInterval(() => {{
      if (motionEnabled && network2d && !is3DMode) {{
        network2d.startSimulation();
      }}
    }}, 250);

    // Animated glowing edge pulses on 2D canvas (locks precisely onto straight edge path)
    network2d.on("afterDrawing", function(ctx) {{
      if (!pulsesEnabled || is3DMode) return;
      const now = performance.now() * 0.001;
      const allEdges = edges.get();
      const positions = network2d.getPositions();

      ctx.save();
      allEdges.forEach((edge, idx) => {{
        const u = positions[edge.from];
        const v = positions[edge.to];
        if (!u || !v) return;

        const dx = v.x - u.x;
        const dy = v.y - u.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 32) return;

        const nodeFrom = nodes.get(edge.from);
        const nodeTo = nodes.get(edge.to);
        const rFrom = nodeFrom ? (nodeFrom.size || 16) : 16;
        const rTo = nodeTo ? (nodeTo.size || 16) : 16;

        // Clip parameter t to travel precisely between outer node perimeters
        const tMin = Math.min((rFrom + 2) / dist, 0.4);
        const tMax = Math.max(1 - (rTo + 8) / dist, 0.6);

        const speed = 0.42;
        const offset = (idx * 0.19) % 1;
        const rawT = (now * speed + offset) % 1;
        const t = tMin + rawT * (tMax - tMin);

        const px = u.x + dx * t;
        const py = u.y + dy * t;

        const isCall = edge.raw && (edge.raw.kind === "calls" || (edge.raw.label && edge.raw.label.toLowerCase().includes("api")));
        const isChange = edge.raw && (edge.raw.kind === "implements" || edge.raw.kind === "corrects");
        const pulseColor = isCall ? "#38bdf8" : (isChange ? "#f43f5e" : "#818cf8");

        // Outer glow
        ctx.beginPath();
        ctx.arc(px, py, 3.6, 0, 2 * Math.PI);
        ctx.fillStyle = pulseColor;
        ctx.shadowColor = pulseColor;
        ctx.shadowBlur = 8;
        ctx.fill();

        // Inner bright core
        ctx.beginPath();
        ctx.arc(px, py, 1.8, 0, 2 * Math.PI);
        ctx.fillStyle = "#ffffff";
        ctx.shadowColor = "#ffffff";
        ctx.shadowBlur = 4;
        ctx.fill();
      }});
      ctx.restore();
    }});

    function animLoop() {{
      if (pulsesEnabled && !is3DMode) {{
        network2d.redraw();
      }}
      requestAnimationFrame(animLoop);
    }}
    requestAnimationFrame(animLoop);

    // ── 3D Galaxy View Implementation ─────────────────────────────────────────
    let highlightNodes3D = new Set();
    let highlightLinks3D = new Set();
    let hoverNode3D = null;

    function createTextSprite(text, color) {{
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      const fontSize = 26;
      ctx.font = `600 ${{fontSize}}px system-ui, -apple-system, sans-serif`;
      const textWidth = ctx.measureText(text).width;
      canvas.width = Math.max(textWidth + 24, 60);
      canvas.height = fontSize + 18;

      // Draw pill background
      ctx.fillStyle = "rgba(7, 10, 19, 0.90)";
      ctx.strokeStyle = color || "#38bdf8";
      ctx.lineWidth = 2.5;

      const r = 8;
      const x = 2, y = 2, w = canvas.width - 4, h = canvas.height - 4;
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + w - r, y);
      ctx.quadraticCurveTo(x + w, y, x + w, y + r);
      ctx.lineTo(x + w, y + h - r);
      ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      ctx.lineTo(x + r, y + h);
      ctx.quadraticCurveTo(x, y + h, x, y + h - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Draw text
      ctx.font = `600 ${{fontSize}}px system-ui, -apple-system, sans-serif`;
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, canvas.width / 2, canvas.height / 2);

      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      const spriteMat = new THREE.SpriteMaterial({{ map: texture, depthWrite: false }});
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(canvas.width / 8.5, canvas.height / 8.5, 1);
      return sprite;
    }}

    function init3DView() {{
      const container3d = document.getElementById("network-3d");
      if (typeof ForceGraph3D === "undefined" || typeof THREE === "undefined") {{
        alert("3D library loading... please check network connection or use 2D Fluid mode.");
        return;
      }}

      // Pre-format nodes for 3D
      const gNodes = rawData.nodes.map(n => {{
        let label = n.title || n.name || n.id;
        if (n.path) {{
          const parts = n.path.split("/").filter(Boolean);
          if (n.kind === "directory") {{
            label = "📁 " + (parts[parts.length - 1] || n.id);
          }} else if (parts.length >= 2) {{
            label = parts.slice(-2).join("/");
          }} else {{
            label = parts[parts.length - 1] || n.id;
          }}
        }} else if (n.kind === "change") {{
          label = (n.change_type === "correction" ? "🔧 " : "✨ ") + (n.title || n.id);
        }} else if (n.kind === "annotation") {{
          label = "📝 " + (n.title || n.id);
        }}
        const color = KIND_COLORS[n.kind] || "#94a3b8";
        return {{
          id: n.id,
          name: label,
          kind: n.kind || "file",
          color: color,
          raw: n,
          neighbors: [],
          links: []
        }};
      }});

      const nodeMap = new Map(gNodes.map(n => [n.id, n]));

      const gLinks = rawData.edges.map(e => {{
        const sourceNode = nodeMap.get(e.source);
        const targetNode = nodeMap.get(e.target);
        const isContainment = e.kind === "contains" || (e.label && e.label.startsWith("contains "));
        const linkObj = {{
          source: e.source,
          target: e.target,
          label: isContainment ? "" : (e.label || e.kind || ""),
          isContainment: isContainment,
          raw: e
        }};
        if (sourceNode && targetNode) {{
          sourceNode.neighbors.push(targetNode);
          targetNode.neighbors.push(sourceNode);
          sourceNode.links.push(linkObj);
          targetNode.links.push(linkObj);
        }}
        return linkObj;
      }});

      const initW = container3d.clientWidth || (window.innerWidth - (sidebarOpen ? 440 : 0));
      const initH = container3d.clientHeight || (window.innerHeight - 56);

      graph3dInstance = ForceGraph3D()(container3d)
        .width(initW)
        .height(initH)
        .backgroundColor("#020617")
        .graphData({{ nodes: gNodes, links: gLinks }})
        .nodeLabel(n => `<b>${{n.raw.path || n.raw.title || n.id}}</b><br><span style='color:${{n.color}}'>Kind: ${{n.kind}}</span>`)
        .nodeThreeObject(node => {{
          const group = new THREE.Group();
          const baseColor = new THREE.Color(node.color);

          let mesh;
          if (node.kind === "directory") {{
            // Planetary Sphere with glowing rings
            const geom = new THREE.SphereGeometry(6.5, 20, 20);
            const mat = new THREE.MeshPhongMaterial({{
              color: baseColor,
              emissive: baseColor,
              emissiveIntensity: 0.35,
              shininess: 90
            }});
            mesh = new THREE.Mesh(geom, mat);
            group.add(mesh);

            // Planetary Ring
            const ringGeom = new THREE.RingGeometry(8.5, 12, 32);
            const ringMat = new THREE.MeshBasicMaterial({{
              color: baseColor,
              side: THREE.DoubleSide,
              transparent: true,
              opacity: 0.45
            }});
            const ring = new THREE.Mesh(ringGeom, ringMat);
            ring.rotation.x = Math.PI / 2.5;
            group.add(ring);
          }} else if (node.kind === "change") {{
            // Ruby gem octahedron
            const geom = new THREE.OctahedronGeometry(6.2);
            const mat = new THREE.MeshPhongMaterial({{
              color: baseColor,
              emissive: baseColor,
              emissiveIntensity: 0.45,
              shininess: 100
            }});
            mesh = new THREE.Mesh(geom, mat);
            group.add(mesh);
          }} else if (node.kind === "agent") {{
            // Tech cuboid
            const geom = new THREE.BoxGeometry(6.5, 6.5, 6.5);
            const mat = new THREE.MeshLambertMaterial({{
              color: baseColor,
              emissive: baseColor,
              emissiveIntensity: 0.25
            }});
            mesh = new THREE.Mesh(geom, mat);
            group.add(mesh);
          }} else {{
            // Luminous sphere for files
            const geom = new THREE.SphereGeometry(4.2, 16, 16);
            const mat = new THREE.MeshPhongMaterial({{
              color: baseColor,
              emissive: baseColor,
              emissiveIntensity: 0.25,
              shininess: 80
            }});
            mesh = new THREE.Mesh(geom, mat);
            group.add(mesh);
          }}

          // Billboard 3D Label Badge
          const sprite = createTextSprite(node.name, node.color);
          sprite.position.y = (node.kind === "directory" ? 10 : 8);
          group.add(sprite);

          return group;
        }})
        .linkWidth(link => {{
          if (highlightLinks3D.size > 0) {{
            return highlightLinks3D.has(link) ? 3.2 : 0.4;
          }}
          return link.isContainment ? 0.8 : 1.6;
        }})
        .linkColor(link => {{
          if (highlightLinks3D.size > 0) {{
            return highlightLinks3D.has(link) ? "#38bdf8" : "rgba(100, 116, 139, 0.08)";
          }}
          const isCall = link.raw && (link.raw.kind === "calls" || (link.raw.label && link.raw.label.toLowerCase().includes("api")));
          const isChange = link.raw && (link.raw.kind === "implements" || link.raw.kind === "corrects");
          return isCall ? "rgba(56, 189, 248, 0.55)" : (isChange ? "rgba(244, 63, 94, 0.55)" : "rgba(148, 163, 184, 0.25)");
        }})
        .linkDirectionalParticles(link => {{
          if (!pulsesEnabled) return 0;
          if (highlightLinks3D.size > 0) {{
            return highlightLinks3D.has(link) ? 5 : 0;
          }}
          return link.isContainment ? 1 : 3;
        }})
        .linkDirectionalParticleSpeed(0.007)
        .linkDirectionalParticleWidth(2.5)
        .linkDirectionalParticleColor(l => {{
          const isCall = l.raw && (l.raw.kind === "calls" || (l.raw.label && l.raw.label.toLowerCase().includes("api")));
          const isChange = l.raw && (l.raw.kind === "implements" || l.raw.kind === "corrects");
          return isCall ? "#38bdf8" : (isChange ? "#f43f5e" : "#818cf8");
        }})
        .onNodeHover(node => {{
          if ((!node && !highlightNodes3D.size) || (node && hoverNode3D === node)) return;
          highlightNodes3D.clear();
          highlightLinks3D.clear();

          if (node) {{
            highlightNodes3D.add(node);
            node.neighbors.forEach(neighbor => highlightNodes3D.add(neighbor));
            node.links.forEach(link => highlightLinks3D.add(link));
          }}
          hoverNode3D = node || null;

          graph3dInstance
            .linkWidth(graph3dInstance.linkWidth())
            .linkColor(graph3dInstance.linkColor())
            .linkDirectionalParticles(graph3dInstance.linkDirectionalParticles());
        }})
        .onNodeClick(n => {{
          inspectNode(n.id, true);
          // Fly camera to node
          const distance = 48;
          const distRatio = 1 + distance/Math.hypot(n.x, n.y, n.z);
          graph3dInstance.cameraPosition(
            {{ x: n.x * distRatio, y: n.y * distRatio, z: n.z * distRatio }},
            n,
            1200
          );
        }});

      // Add Cosmic Starfield to 3D Scene
      const scene = graph3dInstance.scene();
      const starCount = 1800;
      const starGeom = new THREE.BufferGeometry();
      const starPos = new Float32Array(starCount * 3);
      for (let i = 0; i < starCount * 3; i += 3) {{
        starPos[i] = (Math.random() - 0.5) * 3000;
        starPos[i+1] = (Math.random() - 0.5) * 3000;
        starPos[i+2] = (Math.random() - 0.5) * 3000;
      }}
      starGeom.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
      const starMat = new THREE.PointsMaterial({{
        color: 0x93c5fd,
        size: 1.8,
        transparent: true,
        opacity: 0.65
      }});
      const starField = new THREE.Points(starGeom, starMat);
      scene.add(starField);

      // Add ambient and directional lights for specular reflections
      const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
      scene.add(ambientLight);
      const sunLight = new THREE.DirectionalLight(0xbae6fd, 1.2);
      sunLight.position.set(150, 250, 200);
      scene.add(sunLight);

      // Auto-orbiting camera movement
      graph3dInstance.controls().autoRotate = true;
      graph3dInstance.controls().autoRotateSpeed = 0.6;
    }}

    // Toggle 2D / 3D Mode
    document.getElementById("btn-view-mode").onclick = function() {{
      is3DMode = !is3DMode;
      const c2d = document.getElementById("network");
      const c3d = document.getElementById("network-3d");

      if (is3DMode) {{
        this.textContent = "🪐 2D Fluid";
        this.classList.add("active");
        c2d.style.display = "none";
        c3d.style.display = "block";
        if (!graph3dInstance) {{
          init3DView();
        }} else {{
          graph3dInstance.resumeAnimation();
        }}
      }} else {{
        this.textContent = "🌌 3D Galaxy";
        this.classList.remove("active");
        if (graph3dInstance) graph3dInstance.pauseAnimation();
        c3d.style.display = "none";
        c2d.style.display = "block";
        network2d.fit();
      }}
    }};

    // 2D Node click & background click handler (with neighborhood focus)
    network2d.on("click", function(params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        highlightNeighborhood(nodeId);
        inspectNode(nodeId, true);
      }} else {{
        resetHighlight();
      }}
    }});

    function highlightNeighborhood(selectedId) {{
      const connectedNodes = new Set(network2d.getConnectedNodes(selectedId));
      connectedNodes.add(selectedId);
      const connectedEdges = new Set(network2d.getConnectedEdges(selectedId));

      nodes.forEach(n => {{
        if (connectedNodes.has(n.id)) {{
          nodes.update({{ id: n.id, color: {{ background: n.baseColor, border: "#ffffff" }}, opacity: 1 }});
        }} else {{
          nodes.update({{ id: n.id, color: {{ background: "rgba(100, 116, 139, 0.22)", border: "rgba(255,255,255,0.08)" }}, opacity: 0.22 }});
        }}
      }});

      edges.forEach(e => {{
        if (connectedEdges.has(e.id)) {{
          edges.update({{ id: e.id, color: {{ color: "#38bdf8", opacity: 1 }}, width: 2.2 }});
        }} else {{
          edges.update({{ id: e.id, color: {{ color: "rgba(100, 116, 139, 0.08)", opacity: 0.08 }}, width: 1 }});
        }}
      }});
    }}

    function resetHighlight() {{
      nodes.forEach(n => {{
        nodes.update({{ id: n.id, color: {{ background: n.baseColor, border: "#ffffff" }}, opacity: 1 }});
      }});
      edges.forEach(e => {{
        edges.update({{ id: e.id, color: {{ color: "rgba(148, 163, 184, 0.35)", highlight: "#38bdf8" }}, width: 1.5 }});
      }});
    }}

    // Inspector Rendering
    function inspectNode(nodeId, shouldSwitchTab = false) {{
      const n = nodes.get(nodeId) || (rawData.nodes.find(x => x.id === nodeId));
      if (!n) return;
      const raw = n.raw || n;
      if (shouldSwitchTab) {{
        switchTab('inspector');
        if (!sidebarOpen) toggleSidebar(true);
      }}

      const incomingEdges = edges.get({{ filter: e => e.to === nodeId }});
      const outgoingEdges = edges.get({{ filter: e => e.from === nodeId }});

      const html = `
        <div class="node-header">
          <div class="node-title">${{raw.path || raw.title || raw.name || raw.id}}</div>
          <span class="node-kind-tag" style="background:${{KIND_COLORS[raw.kind] || '#94a3b8'}}; color:#090d16;">
            ${{raw.kind || 'file'}}
          </span>
        </div>

        <div class="meta-box">
          <div class="meta-row"><span class="meta-label">Node ID:</span> <code>${{raw.id}}</code></div>
          ${{raw.language ? `<div class="meta-row"><span class="meta-label">Language:</span> <span>${{raw.language}}</span></div>` : ''}}
          ${{raw.change_type ? `<div class="meta-row"><span class="meta-label">Change Type:</span> <span>${{raw.change_type}}</span></div>` : ''}}
          ${{raw.author ? `<div class="meta-row"><span class="meta-label">Author:</span> <span>${{raw.author}}</span></div>` : ''}}
        </div>

        ${{raw.summary ? `<div><div class="section-title">Summary</div><p style="font-size:0.86rem; color:#cbd5e1;">${{raw.summary}}</p></div>` : ''}}
        ${{raw.description ? `<div><div class="section-title">Description</div><p style="font-size:0.86rem; color:#cbd5e1;">${{raw.description}}</p></div>` : ''}}

        ${{raw.context ? `
          <div>
            <div class="section-title">File Content Preview</div>
            <div class="code-preview">${{escapeHtml(raw.context)}}</div>
          </div>
        ` : ''}}

        <div>
          <div class="section-title">Relationships (${{incomingEdges.length + outgoingEdges.length}})</div>
          <div style="font-size:0.82rem; color:#94a3b8; display:flex; flex-direction:column; gap:0.3rem;">
            ${{incomingEdges.map(e => `<div>← <i>${{e.label}}</i> from <a href="javascript:focusNode('${{e.from}}', false)" style="color:#38bdf8;">${{getNodeName(e.from)}}</a></div>`).join('')}}
            ${{outgoingEdges.map(e => `<div>→ <i>${{e.label}}</i> to <a href="javascript:focusNode('${{e.to}}', false)" style="color:#38bdf8;">${{getNodeName(e.to)}}</a></div>`).join('')}}
          </div>
        </div>

        <button class="btn" style="margin-top:0.5rem; justify-content:center; background:rgba(56,189,248,0.15); border-color:#38bdf8; color:#38bdf8;" onclick="askAboutNode('${{nodeId}}')">
          💬 Ask Question About This Node
        </button>
      `;

      document.getElementById("inspector-content").innerHTML = html;
    }}

    function getNodeName(id) {{
      const n = nodes.get(id) || rawData.nodes.find(x => x.id === id);
      return n ? ((n.raw ? n.raw.path : n.path) || (n.raw ? n.raw.title : n.title) || id) : id;
    }}

    function focusNode(nodeId, shouldSwitchTab = false) {{
      if (is3DMode && graph3dInstance) {{
        const gData = graph3dInstance.graphData();
        const n3d = gData.nodes.find(n => n.id === nodeId);
        if (n3d) {{
          const distance = 48;
          const distRatio = 1 + distance/Math.hypot(n3d.x, n3d.y, n3d.z);
          graph3dInstance.cameraPosition(
            {{ x: n3d.x * distRatio, y: n3d.y * distRatio, z: n3d.z * distRatio }},
            n3d,
            1200
          );
        }}
      }} else {{
        network2d.focus(nodeId, {{ scale: 1.2, animation: {{ duration: 300, easingFunction: "easeInOutQuad" }} }});
        network2d.selectNodes([nodeId]);
        highlightNeighborhood(nodeId);
      }}
      inspectNode(nodeId, shouldSwitchTab);
    }}

    // Tab switcher
    function switchTab(tab) {{
      document.getElementById("tab-qa-btn").classList.toggle("active", tab === "qa");
      document.getElementById("tab-inspector-btn").classList.toggle("active", tab === "inspector");
      document.getElementById("tab-qa").classList.toggle("active", tab === "qa");
      document.getElementById("tab-inspector").classList.toggle("active", tab === "inspector");
    }}

    // Toolbar buttons
    document.getElementById("btn-fit").onclick = () => {{
      if (is3DMode && graph3dInstance) {{
        graph3dInstance.zoomToFit(800);
      }} else {{
        network2d.fit({{ animation: {{ duration: 500 }} }});
      }}
    }};

    document.getElementById("btn-motion").onclick = function() {{
      motionEnabled = !motionEnabled;
      this.classList.toggle("active", motionEnabled);
      if (is3DMode && graph3dInstance) {{
        graph3dInstance.controls().autoRotate = motionEnabled;
      }} else if (motionEnabled) {{
        network2d.startSimulation();
      }}
    }};

    document.getElementById("btn-pulses").onclick = function() {{
      pulsesEnabled = !pulsesEnabled;
      this.classList.toggle("active", pulsesEnabled);
      if (is3DMode && graph3dInstance) {{
        graph3dInstance.linkDirectionalParticles(pulsesEnabled ? 3 : 0);
      }}
    }};

    // Clean Labels toggle (clean / none / all)
    let edgeLabelModes = ["clean", "none", "all"];
    let edgeLabelModeIdx = 0;

    function updateEdgeLabels() {{
      const currentMode = edgeLabelModes[edgeLabelModeIdx];
      const btn = document.getElementById("btn-labels");
      if (currentMode === "clean") {{
        btn.textContent = "🏷️ Clean Labels";
        btn.classList.add("active");
      }} else if (currentMode === "none") {{
        btn.textContent = "🏷️ No Edge Labels";
        btn.classList.remove("active");
      }} else {{
        btn.textContent = "🏷️ All Labels";
        btn.classList.add("active");
      }}

      edges.forEach(e => {{
        let newLabel = "";
        const isContainment = e.raw && (e.raw.kind === "contains" || (e.raw.label && e.raw.label.startsWith("contains ")));
        if (currentMode === "clean") {{
          newLabel = isContainment ? "" : (e.raw ? (e.raw.label || e.raw.kind || "") : "");
        }} else if (currentMode === "all") {{
          newLabel = e.raw ? (e.raw.label || e.raw.kind || "") : "";
        }} else {{
          newLabel = "";
        }}
        edges.update({{ id: e.id, label: newLabel }});
      }});
    }}

    document.getElementById("btn-labels").onclick = function() {{
      edgeLabelModeIdx = (edgeLabelModeIdx + 1) % edgeLabelModes.length;
      updateEdgeLabels();
    }};

    // Spacing toggle (Normal: 220px vs Wide: 320px)
    let wideSpacing = false;
    document.getElementById("btn-spacing").onclick = function() {{
      wideSpacing = !wideSpacing;
      this.classList.toggle("active", wideSpacing);
      this.textContent = wideSpacing ? "↔️ Wide Spacing" : "↔️ Spacing";

      network2d.setOptions({{
        physics: {{
          forceAtlas2Based: {{
            springLength: wideSpacing ? 320 : 220,
            gravitationalConstant: wideSpacing ? -300 : -180,
            centralGravity: wideSpacing ? 0.003 : 0.005,
            springConstant: 0.05,
            damping: 0.28,
            avoidOverlap: 1.0
          }}
        }}
      }});
      network2d.startSimulation();
    }};

    let sidebarOpen = true;

    function toggleSidebar(forceState) {{
      if (typeof forceState === "boolean") {{
        sidebarOpen = forceState;
      }} else {{
        sidebarOpen = !sidebarOpen;
      }}

      const sb = document.getElementById("sidebar");
      const navBtn = document.getElementById("btn-toggle-sidebar");
      const floatBtn = document.getElementById("floating-sidebar-toggle");

      if (sidebarOpen) {{
        sb.classList.remove("collapsed");
        if (navBtn) {{
          navBtn.classList.add("active");
          navBtn.textContent = "▶ Collapse Panel";
        }}
        if (floatBtn) floatBtn.classList.remove("visible");
      }} else {{
        sb.classList.add("collapsed");
        if (navBtn) {{
          navBtn.classList.remove("active");
          navBtn.textContent = "◀ Open Panel";
        }}
        if (floatBtn) floatBtn.classList.add("visible");
      }}

      setTimeout(() => {{
        if (is3DMode && graph3dInstance) {{
          const c3d = document.getElementById("network-3d");
          const w = c3d.clientWidth || (window.innerWidth - (sidebarOpen ? 440 : 0));
          const h = c3d.clientHeight || (window.innerHeight - 56);
          graph3dInstance.width(w).height(h);
        }} else if (network2d) {{
          network2d.redraw();
        }}
      }}, 320);
    }}

    document.getElementById("btn-toggle-sidebar").onclick = function() {{
      toggleSidebar();
    }};

    // Search bar
    document.getElementById("search-input").addEventListener("input", function(e) {{
      const val = e.target.value.toLowerCase().trim();
      if (!val) return;
      const match = rawData.nodes.find(n => (n.path && n.path.toLowerCase().includes(val)) || (n.title && n.title.toLowerCase().includes(val)));
      if (match) focusNode(match.id, false);
    }});

    // Deep link permalink support (e.g. #3d, #collapsed, #auth/models.py)
    function checkUrlHash() {{
      if (window.location.hash) {{
        const targetId = decodeURIComponent(window.location.hash.substring(1)).toLowerCase();
        if (targetId === "3d" || targetId === "galaxy") {{
          if (!is3DMode) document.getElementById("btn-view-mode").click();
          return;
        }}
        if (targetId === "collapsed" || targetId === "fullscreen") {{
          toggleSidebar(false);
          return;
        }}
        const found = rawData.nodes.find(n => 
          n.id === targetId || 
          (n.path && (n.path.toLowerCase() === targetId || targetId.endsWith(n.path.toLowerCase()) || n.path.toLowerCase().endsWith(targetId))) ||
          (n.title && n.title.toLowerCase().includes(targetId))
        );
        if (found) {{
          setTimeout(() => focusNode(found.id, false), 200);
        }}
      }}
    }}
    window.addEventListener("load", checkUrlHash);
    window.addEventListener("hashchange", checkUrlHash);

    // ── Client-side Graph Q&A Engine ──────────────────────────────────────────

    function submitQuestion() {{
      const input = document.getElementById("qa-input");
      const question = input.value.trim();
      if (!question) return;
      input.value = "";
      askQuestion(question);
    }}

    function handleKey(e) {{
      if (e.key === "Enter") submitQuestion();
    }}

    function askPreset(q) {{
      askQuestion(q);
    }}

    function askAboutNode(nodeId) {{
      const name = getNodeName(nodeId);
      switchTab('qa');
      if (!sidebarOpen) toggleSidebar(true);
      askQuestion(`What is the context and role of ${{name}}?`);
    }}

    function appendMsg(text, type, citedNodes = []) {{
      const history = document.getElementById("qa-history");
      const div = document.createElement("div");
      div.className = `qa-msg ${{type}}`;

      let content = text.replace(/\\n/g, "<br>").replace(/\\*\\*(.*?)\\*\\*/g, "<b>$1</b>");
      div.innerHTML = content;

      if (citedNodes && citedNodes.length > 0) {{
        const citeBox = document.createElement("div");
        citeBox.style.marginTop = "0.5rem";
        citeBox.innerHTML = "<div style='font-size:0.75rem; color:#94a3b8; margin-bottom:0.2rem;'>📌 Cited Graph Nodes:</div>";
        citedNodes.forEach(nid => {{
          const badge = document.createElement("span");
          badge.className = "cited-badge";
          badge.textContent = getNodeName(nid);
          badge.title = "Click to locate on graph (stays in chat)";
          badge.onclick = () => focusNode(nid, false);
          citeBox.appendChild(badge);
        }});
        div.appendChild(citeBox);
      }}

      history.appendChild(div);
      history.scrollTop = history.scrollHeight;
    }}

    // Graph Question Answering Logic
    async function askQuestion(question) {{
      appendMsg(question, "user");

      // Try server endpoint if available
      try {{
        const resp = await fetch("/api/qa", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ question }})
        }});
        if (resp.ok) {{
          const data = await resp.json();
          appendMsg(data.answer, "assistant", data.cited_nodes);
          if (data.cited_nodes && data.cited_nodes.length > 0) {{
            if (!is3DMode) network2d.selectNodes(data.cited_nodes);
            focusNode(data.cited_nodes[0], false);
          }}
          return;
        }}
      }} catch (err) {{
        // Fall back to client-side graph reasoner
      }}

      // Client-side Graph Intelligence Fallback
      const ans = clientGraphReason(question);
      appendMsg(ans.text, "assistant", ans.cited);
      if (ans.cited && ans.cited.length > 0) {{
        if (!is3DMode) network2d.selectNodes(ans.cited);
        focusNode(ans.cited[0], false);
      }}
    }}

    function clientGraphReason(question) {{
      const q = question.toLowerCase();

      // 1. Implementation
      if (q.includes("implement") || q.includes("built") || q.includes("created") || q.includes("feature")) {{
        const impls = rawData.nodes.filter(n => n.kind === "change" && n.change_type !== "correction");
        const cited = [];
        let text = `Found <b>${{impls.length}}</b> recorded implementation(s):<br><br>`;
        impls.forEach((imp, i) => {{
          cited.push(imp.id);
          if (imp.targets) cited.push(...imp.targets);
          text += `<b>${{i+1}}. ${{imp.title || 'Implementation'}}</b><br>`;
          if (imp.description) text += `> <i>${{imp.description}}</i><br><br>`;
        }});
        return {{ text, cited }};
      }}

      // 2. Correction / Bug fixes
      if (q.includes("correct") || q.includes("fix") || q.includes("bug") || q.includes("error") || q.includes("issue")) {{
        const fixes = rawData.nodes.filter(n => n.kind === "change" && (n.change_type === "correction" || (n.title && n.title.toLowerCase().includes("fix"))));
        const cited = [];
        let text = `Found <b>${{fixes.length}}</b> correction / bug fix record(s):<br><br>`;
        fixes.forEach((fx, i) => {{
          cited.push(fx.id);
          if (fx.targets) cited.push(...fx.targets);
          text += `🔧 <b>${{i+1}}. ${{fx.title}}</b><br>`;
          if (fx.description) text += `> <i>${{fx.description}}</i><br><br>`;
        }});
        return {{ text, cited }};
      }}

      // 3. React to Django / Connections
      if (q.includes("connect") || q.includes("django") || q.includes("react") || q.includes("call") || q.includes("api")) {{
        const callEdges = rawData.edges.filter(e => e.kind === "calls" || (e.label && e.label.toLowerCase().includes("api")));
        const cited = [];
        let text = `<b>Communication & Data Flow:</b><br><br>`;
        if (callEdges.length > 0) {{
          callEdges.forEach(e => {{
            cited.push(e.source, e.target);
            text += `• <b>${{getNodeName(e.source)}}</b> ➔ <i>${{e.label || 'calls'}}</i> ➔ <b>${{getNodeName(e.target)}}</b><br>`;
          }});
          text += `<br>The React application proxies API calls via Vite to the Django backend at <code>/api/hello/</code> and <code>/api/status/</code>.`;
        }} else {{
          text += `Found connection between frontend and backend via API proxy configuration.`;
        }}
        return {{ text, cited }};
      }}

      // 4. Fallback search
      const words = q.split(/\\s+/).filter(w => w.length > 2);
      const matches = rawData.nodes.filter(n => {{
        const text = `${{n.path}} ${{n.title}} ${{n.summary}} ${{n.description}}`.toLowerCase();
        return words.some(w => text.includes(w));
      }}).slice(0, 5);

      if (matches.length > 0) {{
        const cited = matches.map(m => m.id);
        let text = `Relevant items found in the memory graph:<br><br>`;
        matches.forEach(m => {{
          text += `• <b>${{getNodeName(m.id)}}</b> (<code>${{m.kind}}</code>)<br>`;
          if (m.summary || m.description) text += `> ${{m.summary || m.description}}<br>`;
        }});
        return {{ text, cited }};
      }}

      return {{
        text: `I searched the memory graph for "<i>${{question}}</i>". You can ask about recorded implementations, bug corrections, file relationships, or click any node to inspect details.`,
        cited: []
      }};
    }}

    function filterByKind(kind) {{
      const matching = rawData.nodes.filter(n => n.kind === kind).map(n => n.id);
      if (matching.length > 0) {{
        focusNode(matching[0]);
      }}
    }}

    function escapeHtml(str) {{
      return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }}
  </script>
</body>
</html>
"""

    out_path.write_text(html_content, encoding="utf-8")
    return out_path.resolve()


def to_pyvis_html(
    graph: MemoryGraph,
    output: str | Path = "memory_graph.html",
    height: str = "900px",
    width: str = "100%",
    notebook: bool = False,
) -> Path:
    """Render an interactive HTML visualisation via pyvis."""
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
    """Generate a Mermaid flowchart string."""
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
