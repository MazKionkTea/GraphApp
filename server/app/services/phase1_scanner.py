#!/usr/bin/env python3
"""
FASE 1: Static Code Inspection
Memindai struktur Package/Modul/Class/Fungsi
"""

import os
import json
import ast
import csv
import time
import html as html_lib
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box

console = Console()

# ===== KONSTANTA FOLDER =====
OUTPUT_DIR = Path("trace_output")
OUTPUT_DIR.mkdir(exist_ok=True)

JSON_DIR = OUTPUT_DIR / "json"
XML_DIR = OUTPUT_DIR / "xml"          # <-- DITAMBAHKAN
DOT_DIR = OUTPUT_DIR / "dot"
CSV_DIR = OUTPUT_DIR / "csv"
MD_DIR = OUTPUT_DIR / "md"
HTML_DIR = OUTPUT_DIR / "html"
for d in [JSON_DIR, XML_DIR, DOT_DIR, CSV_DIR, MD_DIR, HTML_DIR]:
    d.mkdir(exist_ok=True)


class Phase1Scanner:
    """Fase 1: Static Code Inspection - Memindai struktur Package/Modul/Class/Fungsi"""

    def __init__(self):
        self.project_root: Optional[Path] = None
        self.entities: List[Dict] = []
        self.summary = {
            "packages": 0,
            "modules": 0,
            "classes": 0,
            "functions": 0,
            "total_entities": 0,
        }
        self.is_scan_done = False
        self.package_cache: Dict[Path, str] = {}
        self.current_page: int = 0
        self.page_size: int = 15
        self.filter_type: Optional[str] = None

    # ==================== UTILITY ====================

    def _get_fqn(self, parts: List[str]) -> str:
        return ".".join(parts)

    def _is_package(self, dir_path: Path) -> bool:
        return (dir_path / "__init__.py").exists()

    def _get_relative_path(self, file_path: Path) -> str:
        if self.project_root:
            try:
                return str(file_path.relative_to(self.project_root))
            except ValueError:
                return str(file_path)
        return str(file_path)

    # ==================== PARSING AST ====================

    def _parse_file(self, file_path: Path, package_parts: List[str]) -> List[Dict]:
        result = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            console.print(f"  [yellow]⚠️  Lewati {file_path.name}: {e}[/yellow]")
            return result

        module_name = file_path.stem
        module_fqn = self._get_fqn(package_parts + [module_name])
        package_fqn = self._get_fqn(package_parts) if package_parts else None

        if module_name != "__init__":
            result.append({
                "fqn": module_fqn,
                "type": "module",
                "file_path": self._get_relative_path(file_path),
                "line_start": 1,
                "line_end": 0,
                "parent_fqn": package_fqn,
                "name": module_name,
            })

        class FunctionCollector(ast.NodeVisitor):
            def __init__(self):
                self.classes = {}
                self.functions = []
                self.current_class = None

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
        class_defs = collector.classes
        function_defs = collector.functions

        for class_name, class_node in class_defs.items():
            class_fqn = self._get_fqn([module_fqn, class_name])
            result.append({
                "fqn": class_fqn,
                "type": "class",
                "file_path": self._get_relative_path(file_path),
                "line_start": class_node.lineno,
                "line_end": class_node.end_lineno or class_node.lineno,
                "parent_fqn": module_fqn,
                "name": class_name,
            })

            for node in class_node.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_fqn = self._get_fqn([class_fqn, node.name])
                    result.append({
                        "fqn": method_fqn,
                        "type": "method",
                        "file_path": self._get_relative_path(file_path),
                        "line_start": node.lineno,
                        "line_end": node.end_lineno or node.lineno,
                        "parent_fqn": class_fqn,
                        "name": node.name,
                    })

        for func_node in function_defs:
            func_fqn = self._get_fqn([module_fqn, func_node.name])
            result.append({
                "fqn": func_fqn,
                "type": "function",
                "file_path": self._get_relative_path(file_path),
                "line_start": func_node.lineno,
                "line_end": func_node.end_lineno or func_node.lineno,
                "parent_fqn": module_fqn,
                "name": func_node.name,
            })

        return result

    # ==================== SCANNING UTAMA ====================

    def scan_directory(self, root_path: str) -> bool:
        self.project_root = Path(root_path).resolve()
        if not self.project_root.is_dir():
            return False

        self.entities = []
        self.summary = {"packages": 0, "modules": 0, "classes": 0, "functions": 0, "total_entities": 0}
        self.package_cache = {}

        py_files = list(self.project_root.rglob("*.py"))
        if not py_files:
            console.print("[yellow]⚠️  Tidak ditemukan file .py di direktori ini.[/yellow]")
            self.is_scan_done = True
            return True

        package_dirs = set()
        for file_path in py_files:
            for parent in file_path.parents:
                if parent == self.project_root:
                    break
                if self._is_package(parent):
                    package_dirs.add(parent)

        for pkg_dir in sorted(package_dirs):
            rel_path = pkg_dir.relative_to(self.project_root)
            parts = list(rel_path.parts)
            pkg_fqn = self._get_fqn(parts)
            parent_pkg_fqn = self._get_fqn(parts[:-1]) if len(parts) > 1 and self._is_package(pkg_dir.parent) else None
            self.entities.append({
                "fqn": pkg_fqn,
                "type": "package",
                "file_path": str(rel_path / "__init__.py"),
                "line_start": 1,
                "line_end": 0,
                "parent_fqn": parent_pkg_fqn,
                "name": parts[-1],
            })
            self.summary["packages"] += 1
            self.package_cache[pkg_dir] = pkg_fqn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Memindai file...", total=len(py_files))

            for file_path in py_files:
                progress.update(task, description=f"[cyan]Memproses {file_path.name}")

                rel_path = file_path.relative_to(self.project_root)
                parts = list(rel_path.parts[:-1])
                package_parts = []
                current_dir = self.project_root
                for part in parts:
                    current_dir = current_dir / part
                    if self._is_package(current_dir):
                        package_parts.append(part)
                    else:
                        break

                entities_in_file = self._parse_file(file_path, package_parts)
                self.entities.extend(entities_in_file)

                progress.advance(task)

        for ent in self.entities:
            t = ent["type"]
            if t == "module":
                self.summary["modules"] += 1
            elif t == "class":
                self.summary["classes"] += 1
            elif t in ("method", "function"):
                self.summary["functions"] += 1
        self.summary["total_entities"] = len(self.entities)
        self.is_scan_done = True
        return True

    # ==================== OUTPUT ====================

    def display_tree(self):
        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong.[/yellow]")
            return

        root_label = f"[bold green]📦 {self.project_root.name}[/bold green]"
        tree = Tree(root_label)

        nodes_by_parent = {}
        for ent in self.entities:
            parent = ent.get("parent_fqn")
            if parent not in nodes_by_parent:
                nodes_by_parent[parent] = []
            nodes_by_parent[parent].append(ent)

        root_entities = nodes_by_parent.get(None, [])

        def add_to_tree(parent_tree, parent_fqn):
            children = nodes_by_parent.get(parent_fqn, [])
            for ent in children:
                icon = {
                    "package": "📦",
                    "module": "📄",
                    "class": "🏷️",
                    "method": "🔧",
                    "function": "⚙️"
                }.get(ent["type"], "•")
                color = {
                    "package": "green",
                    "module": "blue",
                    "class": "yellow",
                    "method": "magenta",
                    "function": "cyan"
                }.get(ent["type"], "white")
                label = f"[{color}]{icon} {ent['name']}[/{color}]"
                label += f" [dim](line {ent['line_start']})[/dim]"
                branch = parent_tree.add(label)
                add_to_tree(branch, ent["fqn"])

        for ent in root_entities:
            icon = {
                "package": "📦",
                "module": "📄",
                "class": "🏷️",
                "method": "🔧",
                "function": "⚙️"
            }.get(ent["type"], "•")
            color = {
                "package": "green",
                "module": "blue",
                "class": "yellow",
                "method": "magenta",
                "function": "cyan"
            }.get(ent["type"], "white")
            label = f"[{color}]{icon} {ent['name']}[/{color}]"
            label += f" [dim](line {ent['line_start']})[/dim]"
            branch = tree.add(label)
            add_to_tree(branch, ent["fqn"])

        console.print(tree)

        table = Table(title="📊 Statistik Hasil Scan", style="cyan")
        table.add_column("Jenis", style="bold")
        table.add_column("Jumlah", justify="right")
        table.add_row("📦 Package", str(self.summary["packages"]))
        table.add_row("📄 Module", str(self.summary["modules"]))
        table.add_row("🏷️ Class", str(self.summary["classes"]))
        table.add_row("🔧 Method / ⚙️ Function", str(self.summary["functions"]))
        table.add_row("━━━━━━━━━━━━━━━━━━", "━━━━━━━━━━━")
        table.add_row("📌 Total Entitas", str(self.summary["total_entities"]))
        console.print(table)

    # ---------- EKSPOR KE JSON ----------
    def export_json(self, force: bool = False):
        output_file = JSON_DIR / "phase1_static_map.json"
        if output_file.exists() and not force and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=False):
            console.print("[dim]Ekspor dibatalkan.[/dim]")
            return

        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong. Ekspor dibatalkan.[/yellow]")
            return

        data = {
            "project_root": str(self.project_root),
            "summary": self.summary,
            "entities": self.entities,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✅ File JSON berhasil diekspor ke {output_file}[/green]")

    # ---------- EKSPOR KE XML ----------
    def export_xml(self):
        output_file = XML_DIR / "phase1_static_map.xml"
        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=False):
            console.print("[dim]Ekspor dibatalkan.[/dim]")
            return

        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong. Ekspor dibatalkan.[/yellow]")
            return

        root = ET.Element("project")
        root.set("root_path", str(self.project_root))

        summary_elem = ET.SubElement(root, "summary")
        for key, val in self.summary.items():
            sub = ET.SubElement(summary_elem, key)
            sub.text = str(val)

        entities_elem = ET.SubElement(root, "entities")
        for ent in self.entities:
            ent_elem = ET.SubElement(entities_elem, "entity")
            for k, v in ent.items():
                if v is None:
                    continue
                child = ET.SubElement(ent_elem, k)
                child.text = str(v)

        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(dom.toprettyxml(indent="  "))

        console.print(f"[green]✅ File XML berhasil diekspor ke {output_file}[/green]")

    # ---------- EKSPOR KE MARKDOWN ----------
    def export_md(self):
        output_file = MD_DIR / "phase1_static_map.md"
        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=False):
            console.print("[dim]Ekspor dibatalkan.[/dim]")
            return

        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong. Ekspor dibatalkan.[/yellow]")
            return

        lines = []
        lines.append(f"# Static Code Inspection Report")
        lines.append(f"**Project Root:** `{self.project_root}`\n")
        lines.append("## Summary")
        lines.append("| Jenis | Jumlah |")
        lines.append("|-------|--------|")
        lines.append(f"| Package | {self.summary['packages']} |")
        lines.append(f"| Module | {self.summary['modules']} |")
        lines.append(f"| Class | {self.summary['classes']} |")
        lines.append(f"| Method / Function | {self.summary['functions']} |")
        lines.append(f"| **Total** | **{self.summary['total_entities']}** |")
        lines.append("")
        lines.append("## Entities")
        lines.append("| FQN | Type | Parent | File | Line |")
        lines.append("|-----|------|--------|------|------|")
        for ent in self.entities:
            fqn = ent.get("fqn", "")
            typ = ent.get("type", "")
            parent = ent.get("parent_fqn", "")
            file_path = ent.get("file_path", "")
            line = ent.get("line_start", "")
            lines.append(f"| `{fqn}` | {typ} | `{parent}` | {file_path} | {line} |")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        console.print(f"[green]✅ File Markdown berhasil diekspor ke {output_file}[/green]")

    # ---------- EKSPOR KE DOT ----------
    def export_dot(self):
        output_file = DOT_DIR / "phase1_static_map.dot"
        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=False):
            console.print("[dim]Ekspor dibatalkan.[/dim]")
            return

        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong. Ekspor dibatalkan.[/yellow]")
            return

        type_colors = {
            "package": "#c8e6c9",
            "module": "#bbdefb",
            "class": "#fff9c4",
            "method": "#e1bee7",
            "function": "#b2ebf2",
        }

        dot_lines = [
            "digraph ProjectStructure {",
            "  rankdir=TB;",
            "  splines=ortho;",
            "  nodesep=0.8;",
            "  ranksep=1.0;",
            "  node [shape=box, style=\"rounded\", fontname=\"Arial\", fontsize=12];",
            "  edge [arrowsize=0.6, fontname=\"Arial\", fontsize=10];",
            ""
        ]

        for ent in self.entities:
            fqn = ent["fqn"]
            label = ent["name"]
            typ = ent["type"]
            color = type_colors.get(typ, "#cccccc")
            dot_lines.append(f'  "{fqn}" [label="{label}", fillcolor="{color}", style="filled"];')

        for ent in self.entities:
            parent = ent.get("parent_fqn")
            if parent and parent in [e["fqn"] for e in self.entities]:
                dot_lines.append(f'  "{parent}" -> "{ent["fqn"]}";')

        dot_lines.append("}")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(dot_lines))

        console.print(f"[green]✅ File DOT berhasil diekspor ke {output_file}[/green]")

    # ---------- EKSPOR KE CSV ----------
    def export_csv(self):
        output_file = CSV_DIR / "phase1_static_map.csv"
        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=False):
            console.print("[dim]Ekspor dibatalkan.[/dim]")
            return

        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong. Ekspor dibatalkan.[/yellow]")
            return

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["fqn", "name", "type", "parent_fqn", "file_path", "line_start", "line_end"])
            for ent in self.entities:
                writer.writerow([
                    ent.get("fqn", ""),
                    ent.get("name", ""),
                    ent.get("type", ""),
                    ent.get("parent_fqn", ""),
                    ent.get("file_path", ""),
                    ent.get("line_start", ""),
                    ent.get("line_end", ""),
                ])

        console.print(f"[green]✅ File CSV berhasil diekspor ke {output_file}[/green]")

    # ---------- EKSPOR KE HTML ----------
    def export_html(self):
        output_file = HTML_DIR / "phase1_static_map.html"
        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=False):
            console.print("[dim]Ekspor dibatalkan.[/dim]")
            return

        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong. Ekspor dibatalkan.[/yellow]")
            return

        e = html_lib.escape

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Static Code Inspection Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
h1, h2 {{ color: #2c3e50; }}
.summary {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #3498db; color: white; }}
tr:nth-child(even) {{ background-color: #f9f9f9; }}
.package {{ background-color: #c8e6c9; }}
.module {{ background-color: #bbdefb; }}
.class {{ background-color: #fff9c4; }}
.method {{ background-color: #e1bee7; }}
.function {{ background-color: #b2ebf2; }}
</style>
</head>
<body>
<h1>📊 Static Code Inspection Report</h1>
<div class="summary">
<p><b>Project Root:</b> {e(str(self.project_root))}</p>
<p><b>Total Entities:</b> {self.summary['total_entities']}</p>
<p><b>Packages:</b> {self.summary['packages']} | <b>Modules:</b> {self.summary['modules']} | <b>Classes:</b> {self.summary['classes']} | <b>Methods/Functions:</b> {self.summary['functions']}</p>
</div>

<h2>📋 Entities</h2>
<table>
<tr><th>FQN</th><th>Name</th><th>Type</th><th>Parent</th><th>File</th><th>Line</th></tr>
"""
        for ent in self.entities:
            fqn = e(ent.get("fqn", ""))
            name = e(ent.get("name", ""))
            typ = e(ent.get("type", ""))
            parent = e(ent.get("parent_fqn", ""))
            file_path = e(ent.get("file_path", ""))
            line = ent.get("line_start", "")
            row_class = typ if typ in ("package", "module", "class", "method", "function") else ""
            html += f'<tr class="{row_class}"><td>{fqn}</td><td>{name}</td><td>{typ}</td><td>{parent}</td><td>{file_path}</td><td>{line}</td></tr>'

        html += """
</table>
<p><i>Generated by Phase 1 Scanner</i></p>
</body>
</html>
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        console.print(f"[green]✅ File HTML berhasil diekspor ke {output_file}[/green]")

    # ---------- TAMPILKAN TABEL ENTITAS ----------
    def display_entity_table(self):
        if not self.is_scan_done or not self.entities:
            console.print("[yellow]Belum ada data hasil scan atau data kosong.[/yellow]")
            return

        filter_type = None
        if self.filter_type:
            filter_type = self.filter_type
        else:
            console.print("\n[bold]Filter berdasarkan tipe entitas:[/bold]")
            console.print("[1] Semua (tanpa filter)")
            console.print("[2] Package")
            console.print("[3] Module")
            console.print("[4] Class")
            console.print("[5] Method / Function")
            choice = Prompt.ask("[bold]Pilih filter[/bold]", choices=["1", "2", "3", "4", "5"], default="1")
            if choice == "2":
                filter_type = "package"
            elif choice == "3":
                filter_type = "module"
            elif choice == "4":
                filter_type = "class"
            elif choice == "5":
                filter_type = "function"
            else:
                filter_type = None

        if filter_type == "function":
            filtered = [e for e in self.entities if e.get("type") in ("method", "function")]
        elif filter_type:
            filtered = [e for e in self.entities if e.get("type") == filter_type]
        else:
            filtered = self.entities

        if not filtered:
            console.print(f"[yellow]⚠️  Tidak ada entitas dengan tipe '{filter_type}'.[/yellow]")
            return

        total = len(filtered)
        page = 0
        page_size = 15
        total_pages = (total - 1) // page_size + 1 if total > 0 else 1

        while True:
            console.clear()
            title = f"📋 Daftar Entitas (Halaman {page + 1}/{total_pages})"
            if filter_type:
                title += f" [Filter: {filter_type}]"
            console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))

            start = page * page_size
            end = min(start + page_size, total)
            page_entities = filtered[start:end]

            table = Table(box=box.ROUNDED)
            table.add_column("No", style="bold", width=4)
            table.add_column("FQN", style="cyan", no_wrap=True)
            table.add_column("Type", justify="center")
            table.add_column("Parent", style="dim")
            table.add_column("File", style="dim")

            for i, ent in enumerate(page_entities, start=start + 1):
                fqn = ent.get("fqn", "")
                typ = ent.get("type", "")
                parent = ent.get("parent_fqn", "")
                file_path = ent.get("file_path", "")
                table.add_row(str(i), fqn, typ, parent, file_path)

            console.print(table)

            nav_info = ""
            if page > 0:
                nav_info += "[p] Previous  "
            if page < total_pages - 1:
                nav_info += "[n] Next  "
            nav_info += "[f] Filter  [0] Kembali"

            console.print(f"[dim]Navigasi: {nav_info}[/dim]")
            console.print(f"[dim]Total: {total} entitas[/dim]")

            choice = Prompt.ask("[bold]Pilih opsi[/bold]",
                                choices=["n", "p", "f", "0"] if page > 0 else ["n", "f", "0"])

            if choice == 'n' and page < total_pages - 1:
                page += 1
            elif choice == 'p' and page > 0:
                page -= 1
            elif choice == 'f':
                self.filter_type = None
                self.display_entity_table()
                return
            elif choice == '0':
                return

    # ---------- RESET ----------
    def reset(self):
        self.project_root = None
        self.entities = []
        self.summary = {"packages": 0, "modules": 0, "classes": 0, "functions": 0, "total_entities": 0}
        self.is_scan_done = False
        self.package_cache = {}
        self.filter_type = None
        console.print("[dim]Data hasil scan telah di-reset.[/dim]")


# ==================== MAIN MENU INTERAKTIF ====================

def main():
    scanner = Phase1Scanner()

    console.print(Panel.fit(
        "[bold cyan]🔍 PHASE 1: STATIC CODE INSPECTION[/bold cyan]\n"
        "[dim]Scanning struktur Package / Modul / Class / Fungsi[/dim]",
        border_style="cyan"
    ))

    while True:
        while True:
            path_input = Prompt.ask("[bold]Masukkan path direktori proyek[/bold]")
            if not path_input.strip():
                console.print("[red]Path tidak boleh kosong.[/red]")
                continue

            if scanner.scan_directory(path_input):
                break
            else:
                console.print(f"[red]❌ Direktori tidak ditemukan![/red]")
                console.print(f"[dim]Anda memasukkan: {path_input}[/dim]")
                choice = Prompt.ask(
                    "[bold]Pilih opsi[/bold]",
                    choices=["1", "2", "x"],
                    default="1"
                )
                if choice == "1":
                    continue
                elif choice == "2":
                    scanner.project_root = Path(path_input).resolve()
                    scanner.entities = []
                    scanner.is_scan_done = True
                    break
                else:
                    console.print("[yellow]👋 Keluar dari Phase 1.[/yellow]")
                    return

        while True:
            if not scanner.entities:
                console.print("[yellow]⚠️  Tidak ada entitas ditemukan. Coba scan ulang dengan direktori lain.[/yellow]")

            menu_text = f"""
[bold]📊 Phase 1 - Menu Hasil Scan[/bold]
[dim]Total entitas ditemukan: {scanner.summary['total_entities']}[/dim]

[1] Tampilkan Ringkasan di Terminal (Tree)
[2] Ekspor ke JSON ({JSON_DIR / 'phase1_static_map.json'})
[3] Ekspor ke XML ({XML_DIR / 'phase1_static_map.xml'})
[4] Ekspor ke Markdown ({MD_DIR / 'phase1_static_map.md'})
[5] Ekspor ke DOT ({DOT_DIR / 'phase1_static_map.dot'})
[6] Ekspor ke CSV ({CSV_DIR / 'phase1_static_map.csv'})
[7] Ekspor ke HTML ({HTML_DIR / 'phase1_static_map.html'})
[8] Tampilkan daftar entitas (tabel dengan navigasi)
[0] Scan Ulang (Kembali ke input direktori)
[x] Keluar
"""
            console.print(Panel(menu_text, border_style="cyan"))
            choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "3", "4", "5", "6", "7", "8", "0", "x"])

            if choice == "1":
                scanner.display_tree()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "2":
                scanner.export_json()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "3":
                scanner.export_xml()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "4":
                scanner.export_md()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "5":
                scanner.export_dot()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "6":
                scanner.export_csv()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "7":
                scanner.export_html()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "8":
                scanner.display_entity_table()
                Prompt.ask("[dim]Tekan Enter untuk kembali ke menu[/dim]", default="")
            elif choice == "0":
                scanner.reset()
                break
            else:
                console.print("[yellow]👋 Selesai. Keluar dari Phase 1.[/yellow]")
                return


if __name__ == "__main__":
    main()
