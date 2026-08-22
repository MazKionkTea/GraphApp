"""Phase 3 — Merge & Filter.

Combines Phase 1 entities with Phase 2 call edges, applies user filters.
"""
from typing import Dict, List, Set


def merge(
    entities: List[Dict],
    edges: List[Dict],
    include_external: bool = True,
    project_only_edges: bool = False,
) -> Dict:
    """Returns dict with merged_nodes, merged_edges, summary."""
    # Build FQN → entity map
    entity_map: Dict[str, Dict] = {e["fqn"]: e for e in entities}

    # Collect FQNs from edges
    fqn_set: Set[str] = set()
    for e in edges:
        if e.get("caller_fqn"):
            fqn_set.add(e["caller_fqn"])
        if e.get("callee_fqn"):
            fqn_set.add(e["callee_fqn"])

    # Build merged nodes
    merged_nodes: Dict[str, Dict] = {}
    for fqn in fqn_set:
        if fqn in entity_map:
            ent = entity_map[fqn]
            merged_nodes[fqn] = {
                "fqn": fqn,
                "name": ent.get("name", fqn.split(".")[-1]),
                "kind": ent.get("kind", "unknown"),
                "file_path": ent.get("file_path"),
                "line_start": ent.get("line_start"),
                "line_end": ent.get("line_end"),
                "parent_fqn": ent.get("parent_fqn"),
                "source_type": "project",
            }
        else:
            # External — not in project entities
            merged_nodes[fqn] = {
                "fqn": fqn,
                "name": fqn.split(".")[-1],
                "kind": "external",
                "file_path": None,
                "line_start": None,
                "line_end": None,
                "parent_fqn": None,
                "source_type": "external",
            }

    # Build merged edges
    merged_edges: List[Dict] = []
    for e in edges:
        cfqn = e.get("caller_fqn", "")
        tfqn = e.get("callee_fqn", "")
        if not cfqn or not tfqn:
            continue
        caller_source = merged_nodes.get(cfqn, {}).get("source_type", "external")
        callee_source = merged_nodes.get(tfqn, {}).get("source_type", "external")
        if project_only_edges and (caller_source != "project" or callee_source != "project"):
            continue
        merged_edges.append({
            "caller_fqn": cfqn,
            "callee_fqn": tfqn,
            "call_count": e.get("call_count", 0),
            "file_path": e.get("file_path"),
            "line_number": e.get("line_number"),
            "source_type": e.get("source_type", "project"),
            "caller_source": caller_source,
            "callee_source": callee_source,
            "mode": e.get("mode", "static"),
        })

    # Optionally drop external nodes
    if not include_external:
        keep = {fqn for fqn, n in merged_nodes.items() if n["source_type"] == "project"}
        merged_nodes = {f: n for f, n in merged_nodes.items() if f in keep}
        merged_edges = [e for e in merged_edges if e["caller_fqn"] in keep and e["callee_fqn"] in keep]

    total_nodes = len(merged_nodes)
    project_nodes = sum(1 for n in merged_nodes.values() if n["source_type"] == "project")
    external_nodes = total_nodes - project_nodes
    total_edges = len(merged_edges)
    project_edges = sum(
        1 for e in merged_edges
        if e["caller_source"] == "project" and e["callee_source"] == "project"
    )
    external_edges = total_edges - project_edges

    summary = {
        "total_nodes": total_nodes,
        "project_nodes": project_nodes,
        "external_nodes": external_nodes,
        "total_edges": total_edges,
        "project_edges": project_edges,
        "external_edges": external_edges,
        "include_external_nodes": include_external,
        "filter_project_edges_only": project_only_edges,
    }

    return {
        "nodes": list(merged_nodes.values()),
        "edges": merged_edges,
        "summary": summary,
    }
