"""Phase 1 — Static Code Inspection.

Ports the existing `Phase1Scanner` to scan a Python project and extract
packages, modules, classes, functions, methods.
"""
import ast
from pathlib import Path
from typing import Dict, List, Optional

from app.db.models import CodeFile, Symbol


def _is_package(dir_path: Path) -> bool:
    return (dir_path / "__init__.py").exists()


def _fqn(parts: List[str]) -> str:
    return ".".join(p for p in parts if p)


def _parse_file(file_path: Path, package_parts: List[str], rel_path: str) -> List[Dict]:
    """Parse a single .py file. Returns list of entity dicts."""
    result: List[Dict] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return result

    module_name = file_path.stem
    module_fqn = _fqn(package_parts + [module_name])
    package_fqn = _fqn(package_parts) if package_parts else None

    if module_name != "__init__":
        result.append({
            "fqn": module_fqn, "name": module_name, "kind": "module",
            "file_path": rel_path, "line_start": 1, "line_end": 0,
            "parent_fqn": package_fqn,
        })

    # Collect classes & free functions
    class FunctionCollector(ast.NodeVisitor):
        def __init__(self):
            self.classes: Dict[str, ast.ClassDef] = {}
            self.functions: List[ast.FunctionDef] = []
            self.current_class: Optional[str] = None

        def visit_ClassDef(self, node):
            self.classes[node.name] = node
            old = self.current_class
            self.current_class = node.name
            self.generic_visit(node)
            self.current_class = old

        def visit_FunctionDef(self, node):
            if self.current_class is None:
                self.functions.append(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            if self.current_class is None:
                self.functions.append(node)
            self.generic_visit(node)

    collector = FunctionCollector()
    collector.visit(tree)

    # Classes + methods
    for cname, cnode in collector.classes.items():
        cfqn = _fqn([module_fqn, cname])
        result.append({
            "fqn": cfqn, "name": cname, "kind": "class",
            "file_path": rel_path,
            "line_start": cnode.lineno, "line_end": cnode.end_lineno or cnode.lineno,
            "parent_fqn": module_fqn,
        })
        for stmt in cnode.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mfqn = _fqn([cfqn, stmt.name])
                result.append({
                    "fqn": mfqn, "name": stmt.name, "kind": "method",
                    "file_path": rel_path,
                    "line_start": stmt.lineno, "line_end": stmt.end_lineno or stmt.lineno,
                    "parent_fqn": cfqn,
                })

    # Free functions
    for fnode in collector.functions:
        ffqn = _fqn([module_fqn, fnode.name])
        result.append({
            "fqn": ffqn, "name": fnode.name, "kind": "function",
            "file_path": rel_path,
            "line_start": fnode.lineno, "line_end": fnode.end_lineno or fnode.lineno,
            "parent_fqn": module_fqn,
        })

    return result


def _hash_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def scan_project(project) -> Dict:
    """Phase 1: scan project. Returns a dict with:
        - files: list[CodeFile data]
        - entities: list[Symbol data]
        - summary: dict of counts
    """
    root = Path(project.root_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    py_files = list(root.rglob("*.py"))
    # Filter __init__.py and __pycache__
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    files_data: List[Dict] = []
    entities: List[Dict] = []

    # Detect package directories
    package_dirs = set()
    for fp in py_files:
        for parent in fp.parents:
            if parent == root:
                break
            if _is_package(parent):
                package_dirs.add(parent)

    # Add package entities
    for pkg in sorted(package_dirs):
        rel = pkg.relative_to(root)
        parts = list(rel.parts)
        pkg_fqn = _fqn(parts)
        parent_fqn = _fqn(parts[:-1]) if len(parts) > 1 and _is_package(pkg.parent) else None
        entities.append({
            "fqn": pkg_fqn, "name": parts[-1], "kind": "package",
            "file_path": str(rel / "__init__.py"),
            "line_start": 1, "line_end": 0,
            "parent_fqn": parent_fqn,
        })

    # Scan each .py file
    for fp in py_files:
        rel = fp.relative_to(root)
        rel_str = str(rel)
        # Build package parts based on parent dirs that are packages
        parts = list(rel.parts[:-1])
        package_parts: List[str] = []
        cur = root
        for part in parts:
            cur = cur / part
            if _is_package(cur):
                package_parts.append(part)
            else:
                break

        # File entry
        h = _hash_file(fp)
        try:
            mtime = fp.stat().st_mtime
        except OSError:
            mtime = None
        files_data.append({
            "path": rel_str, "hash": h, "mtime": mtime,
        })
        # Entities in file
        entities.extend(_parse_file(fp, package_parts, rel_str))

    summary = {
        "files": len(files_data),
        "packages": sum(1 for e in entities if e["kind"] == "package"),
        "modules": sum(1 for e in entities if e["kind"] == "module"),
        "classes": sum(1 for e in entities if e["kind"] == "class"),
        "functions": sum(1 for e in entities if e["kind"] in ("function", "method")),
        "total_entities": len(entities),
    }

    return {"files": files_data, "entities": entities, "summary": summary}
