"""
Build and enrich the Nexus Social Platform memory graph.
"""

from ggi import (
    scan_directory,
    save_graph,
    ChangeRecord,
    ContextEdge,
    EdgeKind,
    NodeKind,
    to_interactive_html,
    to_mermaid,
)

def build_nexus_graph():
    # 1. Auto-scan the codebase
    mg = scan_directory(
        "social_platform",
        project_name="Nexus Social Platform",
        include_content_hash=True,
    )

    def find_id(sub: str) -> str | None:
        nodes = mg.find_nodes(path_contains=sub)
        return nodes[0]["id"] if nodes else None

    # Locate key nodes
    auth_srv = find_id("auth/service.py")
    auth_mid = find_id("auth/middleware.py")
    priv_pol = find_id("privacy/policy.py")
    priv_enum = find_id("privacy/enums.py")
    post_srv = find_id("posts/service.py")
    post_rt = find_id("posts/router.py")
    chat_gw = find_id("chat/gateway.py")
    chat_mgr = find_id("chat/manager.py")
    call_sig = find_id("calls/signaling.py")
    call_room = find_id("calls/room_manager.py")
    s3_adapt = find_id("storage/s3_adapter.py")
    vault = find_id("storage/vault.py")
    app_py = find_id("app.py")

    # 2. Add Architectural Dependency Edges
    if app_py:
        for target in [auth_srv, priv_pol, post_srv, chat_gw, call_sig]:
            if target:
                mg.add_edge_simple(app_py, target, EdgeKind.DEPENDS_ON, "orchestrates service")

    if post_srv and priv_pol:
        mg.add_edge_simple(post_srv, priv_pol, EdgeKind.CALLS, "enforces can_view visibility")

    if post_srv and s3_adapt:
        mg.add_edge_simple(post_srv, s3_adapt, EdgeKind.CALLS, "uploads public post media")

    if post_rt and post_srv:
        mg.add_edge_simple(post_rt, post_srv, EdgeKind.CALLS, "dispatches feed queries")

    if chat_gw and auth_srv:
        mg.add_edge_simple(chat_gw, auth_srv, EdgeKind.DEPENDS_ON, "authenticates socket tokens")

    if chat_gw and priv_pol:
        mg.add_edge_simple(chat_gw, priv_pol, EdgeKind.CALLS, "checks DM authorization")

    if chat_gw and chat_mgr:
        mg.add_edge_simple(chat_gw, chat_mgr, EdgeKind.CALLS, "tracks active user sockets")

    if chat_gw and vault:
        mg.add_edge_simple(chat_gw, vault, EdgeKind.CALLS, "stores encrypted DM attachments")

    if call_sig and auth_srv:
        mg.add_edge_simple(call_sig, auth_srv, EdgeKind.DEPENDS_ON, "authenticates caller/callee")

    if call_sig and call_room:
        mg.add_edge_simple(call_sig, call_room, EdgeKind.CALLS, "manages active call rooms")

    if priv_pol and priv_enum:
        mg.add_edge_simple(priv_pol, priv_enum, EdgeKind.IMPORTS, "uses VisibilityLevel enum")

    # 3. Record Implementations
    if priv_pol and priv_enum:
        mg.record_change(ChangeRecord(
            title="Implement Policy-Based Privacy Engine",
            description="Created multi-tier access control supporting PUBLIC, FRIENDS_ONLY, RESTRICTED, and PRIVATE visibility with audit logging.",
            change_type="implementation",
            targets=[priv_pol, priv_enum],
            author="SecurityTeam",
        ))

    if post_srv and post_rt:
        mg.record_change(ChangeRecord(
            title="Implement Posts & Dynamic Feed Service",
            description="Added post publishing, reactions, comment threads, and visibility-filtered feed queries.",
            change_type="implementation",
            targets=[post_srv, post_rt],
            author="FeedTeam",
        ))

    if chat_gw and chat_mgr:
        mg.record_change(ChangeRecord(
            title="Implement Real-time Chat Gateway",
            description="Built direct channel messaging, connection tracking, read receipts, and encrypted delivery.",
            change_type="implementation",
            targets=[chat_gw, chat_mgr],
            author="ChatTeam",
        ))

    if call_sig and call_room:
        mg.record_change(ChangeRecord(
            title="Implement WebRTC Calling & SDP Signaling",
            description="Designed peer-to-peer audio/video calling, SDP offer/answer exchange, and ICE candidate negotiation.",
            change_type="implementation",
            targets=[call_sig, call_room],
            author="MediaTeam",
        ))

    if s3_adapt and vault:
        mg.record_change(ChangeRecord(
            title="Implement Dual Storage Architecture",
            description="Integrated public media CDN for feed assets and encrypted vault storage for private chat items.",
            change_type="implementation",
            targets=[s3_adapt, vault],
            author="InfraTeam",
        ))

    # 4. Record Corrections (Bug Fixes)
    if post_srv:
        mg.record_change(ChangeRecord(
            title="Fix Private Post Leakage in Public Feed Aggregation",
            description="Resolved security flaw where private/friends-only posts leaked into public trending queries by enforcing PrivacyPolicyEngine.can_view() checks across all feed resolvers.",
            change_type="correction",
            targets=[post_srv],
            author="SecurityTeam",
        ))
        mg.annotate(post_srv, "Critical Security Patch: Enforced strict zero-trust privacy checks on all feed queries.", author="SecurityTeam")

    if call_sig:
        mg.record_change(ChangeRecord(
            title="Fix WebRTC SDP Signaling Race Condition in Call Setup",
            description="Resolved peer connection dropouts during concurrent offer/answer exchange by serializing state transitions and queueing early ICE candidates.",
            change_type="correction",
            targets=[call_sig],
            author="MediaTeam",
        ))
        mg.annotate(call_sig, "Stability Patch: ICE candidate queueing enabled to avoid renegotiation collisions.", author="MediaTeam")

    if chat_gw:
        mg.record_change(ChangeRecord(
            title="Fix WebSocket Heartbeat Timeout on Mobile Clients",
            description="Prevented premature disconnects by increasing ping-pong threshold to 45s with exponential reconnect backoff.",
            change_type="correction",
            targets=[chat_gw],
            author="ChatTeam",
        ))

    # 5. Save Graph Outputs
    json_path = save_graph(mg, "nexus_memory_graph.json")
    yaml_path = save_graph(mg, "nexus_memory_graph.yaml", fmt="yaml")
    html_path = to_interactive_html(mg, output="nexus_interactive.html", title="Nexus Social Platform")
    mmd_content = to_mermaid(mg)
    with open("nexus_graph.mmd", "w") as f:
        f.write(mmd_content)

    print(f"Generated Nexus Memory Graph: {mg.summary()}")
    print(f"JSON: {json_path}")
    print(f"YAML: {yaml_path}")
    print(f"Interactive HTML: {html_path}")

if __name__ == "__main__":
    build_nexus_graph()
