"""Phase 4 — Enrichment.

Adds metrics to merged graph: fan-in/out, LOC, entry points, leaf functions,
global statistics.
"""
from collections import defaultdict
from typing import Dict, List


def enrich(nodes: List[Dict], edges: List[Dict]) -> Dict:
    """Enrich each node with metrics. Returns:
        - enriched_nodes: list of nodes with extra fields
        - summary: global stats
    """
    nodes_by_fqn = {n["fqn"]: n for n in nodes}
    edges_by_caller: Dict[str, List[Dict]] = defaultdict(list)
    edges_by_callee: Dict[str, List[Dict]] = defaultdict(list)
    for e in edges:
        if e.get("caller_fqn"):
            edges_by_caller[e["caller_fqn"]].append(e)
        if e.get("callee_fqn"):
            edges_by_callee[e["callee_fqn"]].append(e)

    enriched: List[Dict] = []
    for fqn, node in nodes_by_fqn.items():
        enriched_node = dict(node)
        callee_edges = edges_by_callee.get(fqn, [])
        caller_set = {e["caller_fqn"] for e in callee_edges if e.get("caller_fqn")}
        fan_in = len(caller_set)

        caller_edges = edges_by_caller.get(fqn, [])
        callee_set = {e["callee_fqn"] for e in caller_edges if e.get("callee_fqn")}
        fan_out = len(callee_set)

        line_start = node.get("line_start")
        line_end = node.get("line_end")
        loc = None
        if line_start and line_end:
            loc = line_end - line_start + 1

        total_calls = sum(e.get("call_count", 0) for e in callee_edges)
        total_time = sum(e.get("total_time_seconds", 0) for e in callee_edges)
        avg_duration = (total_time / total_calls) if total_calls > 0 else 0.0

        kind = node.get("kind", "")
        is_entry = False
        is_leaf = False
        if kind in ("function", "method"):
            is_entry = (fan_in == 0)
            is_leaf = (fan_out == 0)

        enriched_node.update({
            "fan_in": fan_in,
            "fan_out": fan_out,
            "loc": loc,
            "total_calls": total_calls,
            "avg_duration_seconds": round(avg_duration, 6),
            "is_entry_point": is_entry,
            "is_leaf": is_leaf,
        })
        enriched.append(enriched_node)

    # Global stats
    function_nodes = [n for n in enriched if n["kind"] in ("function", "method")]
    if not function_nodes:
        summary = {
            "total_nodes": len(enriched),
            "function_nodes": 0,
            "avg_fan_in": 0,
            "avg_fan_out": 0,
            "max_fan_in": 0,
            "max_fan_out": 0,
            "entry_points": [],
            "leaf_functions": [],
        }
    else:
        avg_fan_in = sum(n["fan_in"] for n in function_nodes) / len(function_nodes)
        avg_fan_out = sum(n["fan_out"] for n in function_nodes) / len(function_nodes)
        max_in = max(function_nodes, key=lambda n: n["fan_in"])
        max_out = max(function_nodes, key=lambda n: n["fan_out"])
        entry_points = [n["fqn"] for n in function_nodes if n["is_entry_point"]]
        leaf_functions = [n["fqn"] for n in function_nodes if n["is_leaf"]]
        summary = {
            "total_nodes": len(enriched),
            "function_nodes": len(function_nodes),
            "avg_fan_in": round(avg_fan_in, 2),
            "avg_fan_out": round(avg_fan_out, 2),
            "max_fan_in": max_in["fan_in"],
            "max_fan_in_node": max_in["fqn"],
            "max_fan_out": max_out["fan_out"],
            "max_fan_out_node": max_out["fqn"],
            "entry_points": entry_points,
            "leaf_functions": leaf_functions,
        }

    return {
        "nodes": enriched,
        "summary": summary,
    }
