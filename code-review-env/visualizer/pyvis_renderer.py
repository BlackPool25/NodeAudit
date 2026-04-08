from __future__ import annotations

import json
import re
from importlib import import_module
from pathlib import Path
from typing import Any


STATUS_COLORS = {
    "pending": "#9CA3AF",
    "in_progress": "#F59E0B",
    "approved": "#10B981",
    "changes_requested": "#EF4444",
    "reviewed": "#3B82F6",
}

EDGE_COLORS = {
    "explicit_import": "#2563EB",
    "implicit_dependency": "#F59E0B",
    "intra_file": "#14B8A6",
    "circular": "#DC2626",
}


def _build_network(height: str, width: str) -> Any:
    network_cls = import_module("pyvis.network").Network
    try:
        return network_cls(height=height, width=width, directed=True, notebook=False, cdn_resources="in_line")
    except TypeError:
        # Backward compatible constructor path for older pyvis builds.
        return network_cls(height=height, width=width, directed=True, notebook=False)


def render_graph_html(
    *,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    output_path: str | Path,
    title: str = "GraphReview - Annotated Dependency Graph",
) -> Path:
    net = _build_network(height="900px", width="100%")

    for node in nodes:
        status = str(node.get("status", "pending"))
        net.add_node(
            n_id=str(node["id"]),
            label=str(node.get("label", node["id"])),
            title=str(node.get("title", "")),
            color=STATUS_COLORS.get(status, STATUS_COLORS["pending"]),
            value=float(node.get("size", 1.0)),
            shape="dot",
        )

    for edge in edges:
        edge_type = str(edge.get("edge_type", "explicit_import"))
        edge_title = str(edge.get("title", edge_type))
        formatted_title = f"type: {edge_type}\n{edge_title}"
        net.add_edge(
            source=str(edge["source"]),
            to=str(edge["target"]),
            title=formatted_title,
            color=EDGE_COLORS.get(edge_type, EDGE_COLORS["explicit_import"]),
            value=1.0,
            width=max(1.0, min(float(edge.get("weight", 1.0)) * 1.3, 2.2)),
            arrows="to",
        )

    net.set_options(
        json.dumps(
            {
                "interaction": {
                    "hover": True,
                    "navigationButtons": True,
                    "keyboard": True,
                },
                "physics": {
                    "enabled": True,
                    "stabilization": {
                        "enabled": True,
                        "iterations": 1000,
                        "fit": True,
                    },
                },
                "nodes": {
                    "font": {"size": 14, "face": "monospace"},
                    "borderWidth": 1,
                },
                "edges": {
                    "smooth": {"enabled": False},
                    "arrows": {"to": {"enabled": True, "scaleFactor": 0.35}},
                },
            }
        )
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(output), open_browser=False, notebook=False)

    html = output.read_text(encoding="utf-8")
    html = re.sub(
        r'<link[^>]*cdn\.jsdelivr\.net[^>]*>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<script[^>]*cdn\.jsdelivr\.net[^>]*>\s*</script>\s*',
        "",
        html,
        flags=re.IGNORECASE,
    )
    if "<title>" in html:
        html = html.replace("<title></title>", f"<title>{title}</title>")
    tooltip_style = (
        "<style>"
        ".vis-tooltip {"
        " background: #fffdf8 !important;"
        " border: 1px solid #d6d3d1 !important;"
        " border-radius: 8px !important;"
        " box-shadow: 0 8px 24px rgba(15,23,42,0.15) !important;"
        " color: #1f2937 !important;"
        " font-family: 'IBM Plex Sans','Segoe UI',sans-serif !important;"
        " font-size: 12px !important;"
        " line-height: 1.35 !important;"
        " white-space: pre-wrap !important;"
        " overflow-wrap: anywhere !important;"
        " word-break: break-word !important;"
        " max-width: 420px !important;"
        " padding: 10px 12px !important;"
        " }"
        "</style>"
    )
    html = html.replace("</head>", f"{tooltip_style}</head>")
    bridge_script = (
        "<script>\n"
        "(function () {\n"
        "  function bindNodeClick() {\n"
        "    if (typeof network === 'undefined') {\n"
        "      setTimeout(bindNodeClick, 250);\n"
        "      return;\n"
        "    }\n"
        "    network.on('click', function (params) {\n"
        "      if (!params.nodes || params.nodes.length === 0) { return; }\n"
        "      var moduleId = params.nodes[0];\n"
        "      if (window.parent && window.parent !== window) {\n"
        "        window.parent.postMessage({ type: 'graphreview-node-select', moduleId: moduleId }, '*');\n"
        "      }\n"
        "    });\n"
        "  }\n"
        "  bindNodeClick();\n"
        "})();\n"
        "</script>"
    )
    html = html.replace("</body>", f"{bridge_script}</body>")
    output.write_text(html, encoding="utf-8")
    return output
