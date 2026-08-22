"""Phase 2 — Function Tracing.

Standard (static): AST-based caller→callee edge collection.
Advanced (dynamic): sys.settrace runtime tracing (placeholder for now).
"""
import ast
import sys
from pathlib import Path
from typing import Dict, List, Optional


def _module_name_from_path(file_path: Path, project_root: Path) -> str:
    try:
        rel = file_path.relative_to(project_root)
        parts = list(rel.parts)
        parts[-1] = parts[-1].replace(".py", "")
        return ".".join(parts)
    except ValueError:
        return file_path.stem


def _callee_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
        return node.func.attr
    return "unknown"


def trace_static(project) -> List[Dict]:
    """Standard mode: walk all .py files, collect call edges from AST."""
    root = Path(project.root_path).resolve()
    py_files = [
        f for f in root.rglob("*.py")
        if f.name != "__init__.py" and "__pycache__" not in str(f)
    ]

    all_calls: List[Dict] = []

    class CallCollector(ast.NodeVisitor):
        def __init__(self, module_name: str):
            self.module_name = module_name
            self.class_stack: List[str] = []
            self.function_stack: List[str] = []
            self.calls: List[Dict] = []

        def visit_ClassDef(self, node):
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node):
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_AsyncFunctionDef(self, node):
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_Call(self, node):
            if self.function_stack:
                if self.class_stack:
                    caller = f"{self.module_name}.{'.'.join(self.class_stack)}.{self.function_stack[-1]}"
                else:
                    caller = f"{self.module_name}.{self.function_stack[-1]}"
            else:
                caller = self.module_name
            callee = _callee_name(node) or "unknown"
            self.calls.append({
                "caller_fqn": caller, "callee_fqn": callee,
                "line_number": node.lineno,
            })
            self.generic_visit(node)

    for fp in py_files:
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read(), filename=str(fp))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module_name = _module_name_from_path(fp, root)
        try:
            rel_path = str(fp.relative_to(root))
        except ValueError:
            rel_path = str(fp)
        collector = CallCollector(module_name)
        collector.visit(tree)
        for c in collector.calls:
            # Heuristic: external if callee doesn't look like project symbol
            all_calls.append({
                "caller_fqn": c["caller_fqn"],
                "callee_fqn": c["callee_fqn"],
                "file_path": rel_path,
                "line_number": c["line_number"],
            })

    # Aggregate by (caller, callee) — count occurrences
    edge_map: Dict[tuple, Dict] = {}
    for c in all_calls:
        key = (c["caller_fqn"], c["callee_fqn"])
        if key not in edge_map:
            edge_map[key] = {
                "caller_fqn": c["caller_fqn"],
                "callee_fqn": c["callee_fqn"],
                "call_count": 0,
                "file_path": c["file_path"],
                "line_number": c["line_number"],
                "mode": "static",
            }
        edge_map[key]["call_count"] += 1

    return list(edge_map.values())


def trace_dynamic(project, target_script: Optional[str] = None) -> List[Dict]:
    """Advanced mode: run target script with sys.settrace, capture runtime calls.

    NOTE: This requires the script to actually run safely. For local use, we
    attempt it, but fall back to static if the target can't be executed.
    """
    # Placeholder — for safety, we don't auto-run user scripts. The indexer
    # can be extended to spawn a subprocess if dynamic tracing is desired.
    # For now, return empty list and let Phase 3/4 use the static results.
    return []
