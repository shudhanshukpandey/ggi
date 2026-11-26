"""
Interactive Web Server for GGI Memory Graph Explorer & Question Panel.

Serves the interactive graph UI and provides API endpoints for
graph retrieval and Question-Answering.
"""

from __future__ import annotations

import json
import socketserver
import webbrowser
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

from ggi.graph import MemoryGraph
from ggi.qa import GraphQA
from ggi.serializer import load_graph
from ggi.visualizer import to_interactive_html


class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_server(
    graph_path: str | Path,
    port: int = 8501,
    host: str = "127.0.0.1",
    auto_open: bool = True,
    slm_url: str | None = None,
) -> None:
    """
    Start the interactive GGI UI server.
    """
    graph_file = Path(graph_path).resolve()
    if not graph_file.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_file}")

    graph = load_graph(graph_file)
    qa = GraphQA(graph, slm_url=slm_url)

    # Generate persistent interactive HTML
    html_file = graph_file.parent / f"{graph_file.stem}_interactive.html"
    to_interactive_html(graph, output=html_file)

    class GGIRequestHandler(SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                content = html_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(content)
                return

            if self.path == "/api/graph":
                data = json.dumps(graph.to_dict()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data)
                return

            if self.path.startswith("/api/context"):
                query = self.path.split("?", 1)[-1] if "?" in self.path else ""
                params = dict(qc.split("=", 1) for qc in query.split("&") if "=" in qc)
                nid = params.get("node_id", "")
                ctx = graph.context_for(nid)
                data = json.dumps(ctx).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data)
                return

            self.send_error(404, "Not Found")

        def do_POST(self) -> None:
            if self.path == "/api/qa":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                try:
                    payload = json.loads(body.decode("utf-8"))
                    question = payload.get("question", "")
                    ans = qa.ask(question)
                    data = json.dumps(ans).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(data)
                except Exception as exc:
                    err = json.dumps({"error": str(exc)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(err)
                return

            self.send_error(404, "Not Found")

        def do_OPTIONS(self) -> None:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Connection", "close")
            self.end_headers()

    url = f"http://{host}:{port}/"
    print(f"🧠 GGI Interactive UI running at {url}")
    print(f"📊 Graph: {graph.summary()}")
    print("Press Ctrl+C to stop.")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    with ThreadingServer((host, port), GGIRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down GGI UI server.")
            httpd.server_close()
