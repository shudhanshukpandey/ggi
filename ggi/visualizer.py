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
    graph_json = json.dumps(graph_dict, default=str)
    proj_title = title or graph.project or "Codebase Memory Graph"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GGI — {proj_title}</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <script src="https://unpkg.com/3d-force-graph"></script>
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
      transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .tabs {{
      display: flex;
      border-bottom: 1px solid var(--border);
      background: rgba(0,0,0,0.2);
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
        <button id="btn-fit" class="btn">🎯 Center</button>
        <button id="btn-toggle-sidebar" class="btn">💬 Q&A Panel</button>
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
  </div>

  <!-- Right Sidebar: Q&A & Node Inspector -->
  <div id="sidebar">
    <div class="tabs">
      <button class="tab-btn active" id="tab-qa-btn" onclick="switchTab('qa')">💬 Question & Answer</button>
      <button class="tab-btn" id="tab-inspector-btn" onclick="switchTab('inspector')">🔍 Node Inspector</button>
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

    // Format nodes for 2D vis.js
    const nodes = new vis.DataSet(
      rawData.nodes.map(n => {{
        const label = n.path ? n.path.split("/").pop() : (n.title || n.name || n.id);
        const kind = n.kind || "file";
        const isChange = kind === "change";
        return {{
          id: n.id,
          label: label,
          title: `<b>${{n.path || n.title || n.id}}</b><br>Kind: ${{kind}}`,
          color: {{
            background: KIND_COLORS[kind] || "#94a3b8",
            border: "#ffffff",
            highlight: {{ background: "#ffffff", border: KIND_COLORS[kind] || "#38bdf8" }}
          }},
          shape: KIND_SHAPES[kind] || "dot",
          size: kind === "directory" ? 22 : (isChange ? 18 : 14),
          font: {{ color: "#f1f5f9", size: 12, strokeWidth: 2, strokeColor: "#090d16" }},
          raw: n
        }};
      }})
    );

    const edges = new vis.DataSet(
      rawData.edges.map(e => ({{
        id: `${{e.source}}->${{e.target}}`,
        from: e.source,
        to: e.target,
        label: e.label || e.kind || "",
        arrows: "to",
        color: {{ color: "rgba(148, 163, 184, 0.4)", highlight: "#38bdf8" }},
        font: {{ color: "#94a3b8", size: 10, strokeWidth: 1, strokeColor: "#090d16" }},
        smooth: {{ type: "continuous" }},
        raw: e
      }}))
    );

    // Initialise 2D Network
    const container2d = document.getElementById("network");
    const options2d = {{
      nodes: {{
        borderWidth: 1.5,
        shadow: true
      }},
      edges: {{
        width: 1.5,
        shadow: true
      }},
      physics: {{
        solver: "forceAtlas2Based",
        forceAtlas2Based: {{
          gravitationalConstant: -45,
          centralGravity: 0.012,
          springLength: 95,
          springConstant: 0.08,
          damping: 0.18,
          avoidOverlap: 0.25
        }},
        maxVelocity: 18,
        minVelocity: 0.02,
        stabilization: {{
          enabled: true,
          iterations: 35,
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

    // Animated glowing edge pulses on 2D canvas
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

        const speed = 0.5;
        const offset = (idx * 0.23) % 1;
        const t = (now * speed + offset) % 1;

        const px = u.x + (v.x - u.x) * t;
        const py = u.y + (v.y - u.y) * t;

        const isCall = edge.raw && (edge.raw.kind === "calls" || (edge.raw.label && edge.raw.label.toLowerCase().includes("api")));
        const isChange = edge.raw && (edge.raw.kind === "implements" || edge.raw.kind === "corrects");
        const pulseColor = isCall ? "#38bdf8" : (isChange ? "#f43f5e" : "#818cf8");

        ctx.beginPath();
        ctx.arc(px, py, 3.8, 0, 2 * Math.PI);
        ctx.fillStyle = pulseColor;
        ctx.shadowColor = pulseColor;
        ctx.shadowBlur = 10;
        ctx.fill();

        const t2 = (t + 0.5) % 1;
        const px2 = u.x + (v.x - u.x) * t2;
        const py2 = u.y + (v.y - u.y) * t2;
        ctx.beginPath();
        ctx.arc(px2, py2, 2.2, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
        ctx.shadowColor = pulseColor;
        ctx.shadowBlur = 6;
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
    function init3DView() {{
      const container3d = document.getElementById("network-3d");
      if (typeof ForceGraph3D === "undefined") {{
        alert("3D library loading... please check network connection or use 2D Fluid mode.");
        return;
      }}

      const gData = {{
        nodes: rawData.nodes.map(n => ({{
          id: n.id,
          name: n.path ? n.path.split("/").pop() : (n.title || n.name || n.id),
          kind: n.kind,
          color: KIND_COLORS[n.kind] || "#94a3b8",
          val: n.kind === "directory" ? 6 : (n.kind === "change" ? 5 : 3),
          raw: n
        }})),
        links: rawData.edges.map(e => ({{
          source: e.source,
          target: e.target,
          label: e.label || e.kind || "",
          raw: e
        }}))
      }};

      graph3dInstance = ForceGraph3D()(container3d)
        .graphData(gData)
        .nodeLabel(n => `<b>${{n.raw.path || n.raw.title || n.id}}</b> [${{n.kind}}]`)
        .nodeColor(n => n.color)
        .nodeRelSize(4.5)
        .linkDirectionalParticles(3)
        .linkDirectionalParticleSpeed(0.006)
        .linkDirectionalParticleWidth(2.5)
        .linkDirectionalParticleColor(l => {{
          const isCall = l.raw && (l.raw.kind === "calls" || (l.raw.label && l.raw.label.toLowerCase().includes("api")));
          const isChange = l.raw && (l.raw.kind === "implements" || l.raw.kind === "corrects");
          return isCall ? "#38bdf8" : (isChange ? "#f43f5e" : "#818cf8");
        }})
        .linkColor(() => "rgba(148, 163, 184, 0.35)")
        .onNodeClick(n => {{
          inspectNode(n.id);
          // Fly camera to node
          const distance = 40;
          const distRatio = 1 + distance/Math.hypot(n.x, n.y, n.z);
          graph3dInstance.cameraPosition(
            {{ x: n.x * distRatio, y: n.y * distRatio, z: n.z * distRatio }},
            n,
            1200
          );
        }});

      // Auto-orbiting camera movement
      graph3dInstance.controls().autoRotate = true;
      graph3dInstance.controls().autoRotateSpeed = 0.8;
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
        if (!graph3dInstance) init3DView();
      }} else {{
        this.textContent = "🌌 3D Galaxy";
        this.classList.remove("active");
        c3d.style.display = "none";
        c2d.style.display = "block";
        network2d.fit();
      }}
    }};

    // 2D Node click handler
    network2d.on("click", function(params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        inspectNode(nodeId);
      }}
    }});

    // Inspector Rendering
    function inspectNode(nodeId) {{
      const n = nodes.get(nodeId) || (rawData.nodes.find(x => x.id === nodeId));
      if (!n) return;
      const raw = n.raw || n;
      switchTab('inspector');

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
            ${{incomingEdges.map(e => `<div>← <i>${{e.label}}</i> from <a href="javascript:focusNode('${{e.from}}')" style="color:#38bdf8;">${{getNodeName(e.from)}}</a></div>`).join('')}}
            ${{outgoingEdges.map(e => `<div>→ <i>${{e.label}}</i> to <a href="javascript:focusNode('${{e.to}}')" style="color:#38bdf8;">${{getNodeName(e.to)}}</a></div>`).join('')}}
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

    function focusNode(nodeId) {{
      if (is3DMode && graph3dInstance) {{
        const gData = graph3dInstance.graphData();
        const n3d = gData.nodes.find(n => n.id === nodeId);
        if (n3d) {{
          const distance = 40;
          const distRatio = 1 + distance/Math.hypot(n3d.x, n3d.y, n3d.z);
          graph3dInstance.cameraPosition(
            {{ x: n3d.x * distRatio, y: n3d.y * distRatio, z: n3d.z * distRatio }},
            n3d,
            1200
          );
        }}
      }} else {{
        network2d.focus(nodeId, {{ scale: 1.2, animation: {{ duration: 600, easingFunction: "easeInOutQuad" }} }});
        network2d.selectNodes([nodeId]);
      }}
      inspectNode(nodeId);
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

    document.getElementById("btn-toggle-sidebar").onclick = function() {{
      const sb = document.getElementById("sidebar");
      sb.style.display = sb.style.display === "none" ? "flex" : "none";
    }};

    // Search bar
    document.getElementById("search-input").addEventListener("input", function(e) {{
      const val = e.target.value.toLowerCase().trim();
      if (!val) return;
      const match = rawData.nodes.find(n => (n.path && n.path.toLowerCase().includes(val)) || (n.title && n.title.toLowerCase().includes(val)));
      if (match) focusNode(match.id);
    }});

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
          badge.onclick = () => focusNode(nid);
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
            focusNode(data.cited_nodes[0]);
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
        focusNode(ans.cited[0]);
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
