#!/usr/bin/env python3
"""
FASE 3: Merge & Filter
Menggabungkan data tracing dari Fase 2 dengan struktur proyek dari Fase 1,
serta menerapkan filter pilihan user.
Output: JSON, XML, DOT, Markdown, CSV
"""

import json
import sys
import csv
import time
import traceback
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box

console = Console()

# ===== KONSTANTA FOLDER =====
OUTPUT_DIR = Path("trace_output")
OUTPUT_DIR.mkdir(exist_ok=True)

JSON_DIR = OUTPUT_DIR / "json"
XML_DIR = OUTPUT_DIR / "xml"
DOT_DIR = OUTPUT_DIR / "dot"
MD_DIR = OUTPUT_DIR / "md"
CSV_DIR = OUTPUT_DIR / "csv"
for d in [JSON_DIR, XML_DIR, DOT_DIR, MD_DIR, CSV_DIR]:
    d.mkdir(exist_ok=True)

# ===== FILE INPUT =====
PHASE1_FILE = JSON_DIR / "phase1_static_map.json"
if not PHASE1_FILE.exists():
    PHASE1_FILE = OUTPUT_DIR / "phase1_static_map.json"

STANDARD_FILE = JSON_DIR / "phase2_standard_graph.json"
if not STANDARD_FILE.exists():
    STANDARD_FILE = OUTPUT_DIR / "phase2_standard_graph.json"
ADVANCED_FILE = JSON_DIR / "phase2_advanced_graph.json"
if not ADVANCED_FILE.exists():
    ADVANCED_FILE = OUTPUT_DIR / "phase2_advanced_graph.json"


class Phase3Merger:
    def __init__(self):
        self.source_type: Optional[str] = None
        self.include_external_nodes: bool = True
        self.filter_project_edges_only: bool = False

        self.phase1_entities: Dict[str, Dict] = {}
        self.phase1_summary: Dict = {}

        self.raw_edges: List[Dict] = []
        self.raw_summary: Dict = {}
        self.raw_session: Dict = {}

        self.merged_nodes: Dict[str, Dict] = {}
        self.merged_edges: List[Dict] = []
        self.merged_summary: Dict = {}

        self.last_merge_result: Optional[Dict] = None
        self.last_merge_summary: Optional[Dict] = None
        self.last_node_list: Optional[List[Dict]] = None
        self.last_edge_list: Optional[List[Dict]] = None

        self._load_phase1()

    # ==================== LOAD ====================

    def _load_phase1(self):
        if not PHASE1_FILE.exists():
            console.print(f"[red]❌ File {PHASE1_FILE} tidak ditemukan. Jalankan Fase 1 terlebih dahulu.[/red]")
            console.print("[yellow]Pastikan file ada di: trace_output/json/phase1_static_map.json[/yellow]")
            sys.exit(1)

        try:
            with open(PHASE1_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.phase1_summary = data.get("summary", {})
                for ent in data.get("entities", []):
                    fqn = ent.get("fqn")
                    if fqn:
                        self.phase1_entities[fqn] = ent
            console.print(f"[green]✅ Data Fase 1 dimuat: {len(self.phase1_entities)} entitas.[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal membaca {PHASE1_FILE}: {e}[/red]")
            sys.exit(1)

    def _load_phase2_data(self):
        if self.source_type == "standard":
            file_path = STANDARD_FILE
        elif self.source_type == "advanced":
            file_path = ADVANCED_FILE
        else:
            console.print("[red]❌ Sumber data belum dipilih.[/red]")
            return False

        if not file_path.exists():
            console.print(f"[red]❌ File {file_path} tidak ditemukan. Jalankan Fase 2 terlebih dahulu.[/red]")
            console.print(f"[yellow]Pastikan file ada di: trace_output/json/{file_path.name}[/yellow]")
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    console.print(f"[red]❌ File {file_path.name} kosong. Jalankan ulang Fase 2.[/red]")
                    return False
                data = json.loads(content)
                self.raw_edges = data.get("edges", [])
                self.raw_summary = data.get("summary", {})
                self.raw_session = data.get("session_info", {})
            console.print(f"[green]✅ Data {self.source_type} dimuat: {len(self.raw_edges)} edge.[/green]")
            return True
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ File {file_path.name} rusak: {e}[/red]")
            console.print("[yellow]Jalankan ulang Fase 2.[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Gagal membaca {file_path}: {e}[/red]")
            return False

    # ==================== PROSES ====================

    def process(self):
        """Proses utama: merge dan filter, lalu tampilkan menu pasca-merge."""
        console.print("\n[bold cyan]▶️  Memulai proses merge & filter...[/bold cyan]")

        if self.source_type is None:
            console.print("[red]❌ Sumber data belum dipilih. Gunakan menu [1] dulu.[/red]")
            Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            return

        if not self._load_phase2_data():
            console.print("[red]❌ Gagal memuat data Fase 2. Proses dibatalkan.[/red]")
            Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            return

        if not self.raw_edges:
            console.print("[yellow]⚠️  Tidak ada edge ditemukan. Proses dibatalkan.[/yellow]")
            Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            return

        console.print("[cyan]🔄 Menggabungkan data...[/cyan]")

        try:
            node_set: Set[str] = set()
            for edge in self.raw_edges:
                caller = edge.get("caller_fqn", "")
                callee = edge.get("callee_fqn", "")
                if caller:
                    node_set.add(caller)
                if callee:
                    node_set.add(callee)

            if not node_set:
                console.print("[yellow]⚠️  Tidak ada FQN valid di edge. Proses dibatalkan.[/yellow]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                return

            console.print(f"[dim]   → {len(node_set)} node unik ditemukan.[/dim]")

            self.merged_nodes = {}
            for fqn in node_set:
                if fqn in self.phase1_entities:
                    ent = self.phase1_entities[fqn]
                    self.merged_nodes[fqn] = {
                        "fqn": fqn,
                        "name": ent.get("name", fqn.split(".")[-1]),
                        "type": ent.get("type", "unknown"),
                        "file_path": ent.get("file_path"),
                        "line_start": ent.get("line_start"),
                        "line_end": ent.get("line_end"),
                        "parent_fqn": ent.get("parent_fqn"),
                        "source_type": "project"
                    }
                else:
                    self.merged_nodes[fqn] = {
                        "fqn": fqn,
                        "name": fqn.split(".")[-1],
                        "type": "external",
                        "file_path": None,
                        "line_start": None,
                        "line_end": None,
                        "parent_fqn": None,
                        "source_type": "external"
                    }
            console.print(f"[dim]   → {len(self.merged_nodes)} node dibuat.[/dim]")

            self.merged_edges = []
            for edge in self.raw_edges:
                caller_fqn = edge.get("caller_fqn", "")
                callee_fqn = edge.get("callee_fqn", "")
                if not caller_fqn or not callee_fqn:
                    continue

                caller_source = self.merged_nodes.get(caller_fqn, {}).get("source_type", "external")
                callee_source = self.merged_nodes.get(callee_fqn, {}).get("source_type", "external")

                if self.filter_project_edges_only and (caller_source != "project" or callee_source != "project"):
                    continue

                self.merged_edges.append({
                    "caller_fqn": caller_fqn,
                    "callee_fqn": callee_fqn,
                    "call_count": edge.get("call_count", 0),
                    "total_time_seconds": edge.get("total_time_seconds", 0),
                    "avg_time_seconds": edge.get("avg_time_seconds", 0),
                    "source_type": edge.get("source_type", "project"),
                    "mode": edge.get("mode", "static"),
                    "caller_source": caller_source,
                    "callee_source": callee_source,
                })
            console.print(f"[dim]   → {len(self.merged_edges)} edge diproses.[/dim]")

            if not self.include_external_nodes:
                nodes_to_keep = {
                    fqn for fqn, node in self.merged_nodes.items()
                    if node.get("source_type") == "project"
                }
                self.merged_nodes = {
                    fqn: node for fqn, node in self.merged_nodes.items()
                    if fqn in nodes_to_keep
                }
                self.merged_edges = [
                    edge for edge in self.merged_edges
                    if edge["caller_fqn"] in nodes_to_keep and edge["callee_fqn"] in nodes_to_keep
                ]
                console.print(f"[dim]   → Filter node eksternal: {len(self.merged_nodes)} node tersisa.[/dim]")

            total_nodes = len(self.merged_nodes)
            project_nodes = sum(1 for n in self.merged_nodes.values() if n.get("source_type") == "project")
            external_nodes = total_nodes - project_nodes

            total_edges = len(self.merged_edges)
            project_edges = sum(1 for e in self.merged_edges if e.get("caller_source") == "project" and e.get("callee_source") == "project")
            external_edges = total_edges - project_edges

            self.merged_summary = {
                "total_nodes": total_nodes,
                "project_nodes": project_nodes,
                "external_nodes": external_nodes,
                "total_edges": total_edges,
                "project_edges": project_edges,
                "external_edges": external_edges,
                "source_data": self.source_type,
                "include_external_nodes": self.include_external_nodes,
                "filter_project_edges_only": self.filter_project_edges_only,
            }

            self.last_merge_result = {
                "session_info": {
                    "source_type": self.source_type,
                    "phase1_entities": len(self.phase1_entities),
                    "raw_edges": len(self.raw_edges),
                    "include_external_nodes": self.include_external_nodes,
                    "filter_project_edges_only": self.filter_project_edges_only,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "nodes": list(self.merged_nodes.values()),
                "edges": self.merged_edges,
                "summary": self.merged_summary,
            }
            self.last_node_list = list(self.merged_nodes.values())
            self.last_edge_list = self.merged_edges
            self.last_merge_summary = self.merged_summary

            console.print("[green]✅ Proses merge & filter selesai![/green]")
            self._display_summary()
            self._show_post_merge_menu()

        except Exception as e:
            console.print(f"[red]❌ Error saat proses: {e}[/red]")
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
            console.print("[yellow]Silakan perbaiki error di atas, lalu ulangi proses.[/yellow]")
            if self.last_merge_result:
                console.print("[dim]Data sebagian sudah tersedia, mencoba menampilkan menu...[/dim]")
                self._show_post_merge_menu()

    # ==================== MENU PASCA-MERGE ====================

    def _show_post_merge_menu(self):
        """Tampilkan menu setelah merge selesai dengan opsi ekspor dan daftar edge."""
        while True:
            try:
                console.clear()
                console.print(Panel.fit(
                    "[bold green]✅ Proses Merge & Filter selesai![/bold green]",
                    border_style="green"
                ))

                summary = self.last_merge_summary or {}
                if summary:
                    console.print(f"[dim]Total node: {summary.get('total_nodes', 0)}[/dim]")
                    console.print(f"[dim]Project nodes: {summary.get('project_nodes', 0)} | External nodes: {summary.get('external_nodes', 0)}[/dim]")
                    console.print(f"[dim]Total edge: {summary.get('total_edges', 0)}[/dim]")
                    console.print(f"[dim]Project edges: {summary.get('project_edges', 0)} | External edges: {summary.get('external_edges', 0)}[/dim]")
                else:
                    console.print("[yellow]⚠️  Tidak ada data untuk ditampilkan. Jalankan proses terlebih dahulu (menu 4).[/yellow]")

                console.print("\n[bold]Pilih tindakan selanjutnya:[/bold]\n")
                console.print(f"[1] Ekspor JSON -> [yellow]{JSON_DIR / 'phase3_merged.json'}[/yellow]")
                console.print(f"[2] Ekspor XML -> [yellow]{XML_DIR / 'phase3_merged.xml'}[/yellow]")
                console.print(f"[3] Ekspor DOT -> [yellow]{DOT_DIR / 'phase3_merged.dot'}[/yellow]")
                console.print(f"[4] Ekspor Markdown -> [yellow]{MD_DIR / 'phase3_merged.md'}[/yellow]")
                console.print(f"[5] Ekspor CSV -> [yellow]{CSV_DIR / 'phase3_merged.csv'}[/yellow]")
                console.print("[6] Tampilkan ringkasan (ulang)")
                console.print("[7] Tampilkan daftar edge (relasi panggilan)")  # OPSI BARU
                console.print("[0] Kembali ke menu utama Fase 3")
                console.print("[x] Keluar")

                choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "3", "4", "5", "6", "7", "0", "x"])

                if choice == "1":
                    self._export_json()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "2":
                    self._export_xml()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "3":
                    self._export_dot()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "4":
                    self._export_md()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "5":
                    self._export_csv()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "6":
                    self._display_summary()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "7":
                    self._display_edge_list()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "0":
                    return
                else:  # x
                    console.print("[yellow]👋 Keluar dari Fase 3.[/yellow]")
                    sys.exit(0)
            except Exception as e:
                console.print(f"[red]❌ Error di menu: {e}[/red]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    # ==================== DAFTAR EDGE LENGKAP ====================

    def _display_edge_list(self):
        """Tampilkan daftar edge dengan FQN lengkap dan navigasi halaman."""
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data edge untuk ditampilkan.[/yellow]")
            return

        total = len(self.last_edge_list)
        page = 0
        page_size = 15
        total_pages = (total - 1) // page_size + 1 if total > 0 else 1

        while True:
            console.clear()
            console.print(Panel.fit(
                f"[bold cyan]📋 Daftar Edge (Halaman {page + 1}/{total_pages})[/bold cyan]",
                border_style="cyan"
            ))

            start = page * page_size
            end = min(start + page_size, total)
            page_edges = self.last_edge_list[start:end]

            if not page_edges:
                console.print("[yellow]⚠️  Tidak ada edge untuk ditampilkan.[/yellow]")
                break

            table = Table(box=box.ROUNDED)
            table.add_column("No", style="bold", width=4)
            table.add_column("Caller (FQN)", style="cyan", no_wrap=True)
            table.add_column("➡️", width=4)
            table.add_column("Callee (FQN)", style="green", no_wrap=True)
            table.add_column("Caller Source", justify="center")
            table.add_column("Callee Source", justify="center")
            table.add_column("Call Count", justify="right")

            for i, edge in enumerate(page_edges, start=start + 1):
                caller = edge.get("caller_fqn", "")
                callee = edge.get("callee_fqn", "")
                caller_source = edge.get("caller_source", "project")
                callee_source = edge.get("callee_source", "project")
                call_count = edge.get("call_count", 0)

                # Tampilkan FQN lengkap tanpa pemotongan
                table.add_row(
                    str(i),
                    caller,
                    "→",
                    callee,
                    caller_source,
                    callee_source,
                    str(call_count)
                )

            console.print(table)

            nav_info = ""
            if page > 0:
                nav_info += "[p] Previous  "
            if page < total_pages - 1:
                nav_info += "[n] Next  "
            nav_info += "[0] Kembali"

            console.print(f"[dim]Navigasi: {nav_info}[/dim]")
            console.print(f"[dim]Total: {total} edge[/dim]")

            choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["n", "p", "0"] if page > 0 else ["n", "0"])

            if choice == 'n' and page < total_pages - 1:
                page += 1
            elif choice == 'p' and page > 0:
                page -= 1
            elif choice == '0':
                return

    # ==================== EKSPOR ====================

    def _export_json(self):
        try:
            if not self.last_merge_result:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = JSON_DIR / "phase3_merged.json"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.last_merge_result, f, indent=2, ensure_ascii=False)

            console.print(f"[green]✅ JSON berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor JSON: {e}[/red]")

    def _export_xml(self):
        try:
            if not self.last_node_list:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = XML_DIR / "phase3_merged.xml"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            root = ET.Element("merged_graph")
            session = ET.SubElement(root, "session_info")
            for k, v in (self.last_merge_result or {}).get("session_info", {}).items():
                e = ET.SubElement(session, k)
                e.text = str(v)

            summary = ET.SubElement(root, "summary")
            for k, v in (self.last_merge_summary or {}).items():
                e = ET.SubElement(summary, k)
                e.text = str(v)

            nodes_elem = ET.SubElement(root, "nodes")
            for node in self.last_node_list:
                n = ET.SubElement(nodes_elem, "node")
                for k, v in node.items():
                    if v is None:
                        continue
                    child = ET.SubElement(n, k)
                    child.text = str(v)

            edges_elem = ET.SubElement(root, "edges")
            for edge in self.last_edge_list:
                e = ET.SubElement(edges_elem, "edge")
                for k, v in edge.items():
                    child = ET.SubElement(e, k)
                    child.text = str(v)

            xml_str = ET.tostring(root, encoding="unicode")
            dom = minidom.parseString(xml_str)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(dom.toprettyxml(indent="  "))

            console.print(f"[green]✅ XML berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor XML: {e}[/red]")

    def _export_dot(self):
        try:
            if not self.last_node_list or not self.last_edge_list:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = DOT_DIR / "phase3_merged.dot"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            type_colors = {
                "package": "#c8e6c9",
                "module": "#bbdefb",
                "class": "#fff9c4",
                "method": "#e1bee7",
                "function": "#b2ebf2",
                "external": "#eeeeee",
                "unknown": "#cccccc"
            }

            dot_lines = [
                "digraph MergedGraph {",
                "  rankdir=TB;",
                "  splines=ortho;",
                "  nodesep=0.8;",
                "  ranksep=1.0;",
                "  node [shape=box, style=\"rounded\", fontname=\"Arial\", fontsize=12];",
                "  edge [arrowsize=0.6, fontname=\"Arial\", fontsize=10];",
                ""
            ]

            for node in sorted(self.last_node_list, key=lambda x: x.get("fqn", "")):
                nid = node.get("fqn", "")
                label = node.get("name", nid)
                source_type = node.get("source_type", "project")
                node_type = node.get("type", "unknown")

                if source_type == "external":
                    color = "#eeeeee"
                else:
                    color = type_colors.get(node_type, "#cccccc")

                dot_lines.append(f'  "{nid}" [label="{label}", fillcolor="{color}", style="filled"];')

            for edge in self.last_edge_list:
                src = edge.get("caller_fqn", "")
                tgt = edge.get("callee_fqn", "")
                count = edge.get("call_count", 0)
                is_external = edge.get("caller_source") == "external" or edge.get("callee_source") == "external"
                color = "#ef5350" if is_external else "#42a5f5"
                dash = "5,5" if is_external else "0"
                attrs = [f'color="{color}"']
                if dash != "0":
                    attrs.append('style="dashed"')
                if count > 20:
                    attrs.append('penwidth=2.5')
                elif count > 5:
                    attrs.append('penwidth=1.8')
                if count > 0:
                    attrs.append(f'label="{count}"')
                dot_lines.append(f'  "{src}" -> "{tgt}" [' + ", ".join(attrs) + "];")

            dot_lines.append("}")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(dot_lines))

            console.print(f"[green]✅ DOT berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor DOT: {e}[/red]")

    def _export_md(self):
        try:
            if not self.last_node_list or not self.last_edge_list:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = MD_DIR / "phase3_merged.md"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            lines = []
            lines.append("# Hasil Merge & Filter")
            lines.append("")
            lines.append(f"**Sumber Data:** {self.source_type.capitalize()}")
            lines.append(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            lines.append("## Summary")
            summary = self.last_merge_summary or {}
            lines.append("| Metrik | Jumlah |")
            lines.append("|--------|--------|")
            lines.append(f"| Total Node | {summary.get('total_nodes', 0)} |")
            lines.append(f"| Node Project | {summary.get('project_nodes', 0)} |")
            lines.append(f"| Node Eksternal | {summary.get('external_nodes', 0)} |")
            lines.append(f"| Total Edge | {summary.get('total_edges', 0)} |")
            lines.append(f"| Edge Project↔Project | {summary.get('project_edges', 0)} |")
            lines.append(f"| Edge melibatkan Eksternal | {summary.get('external_edges', 0)} |")
            lines.append(f"| Sertakan eksternal | {'Ya' if summary.get('include_external_nodes', True) else 'Tidak'} |")
            lines.append(f"| Filter edge projek saja | {'Ya' if summary.get('filter_project_edges_only', False) else 'Tidak'} |")
            lines.append("")
            lines.append("## Nodes")
            lines.append("| FQN | Name | Type | Source | Parent | File |")
            lines.append("|-----|------|------|--------|--------|------|")
            for node in self.last_node_list:
                fqn = node.get("fqn", "")
                name = node.get("name", "")
                typ = node.get("type", "")
                source = node.get("source_type", "")
                parent = node.get("parent_fqn", "")
                file_path = node.get("file_path", "")
                lines.append(f"| `{fqn}` | {name} | {typ} | {source} | `{parent}` | {file_path} |")
            lines.append("")
            lines.append("## Edges")
            lines.append("| No | Caller (FQN) | Callee (FQN) | Caller Source | Callee Source | Call Count |")
            lines.append("|----|--------------|--------------|---------------|---------------|------------|")
            for idx, edge in enumerate(self.last_edge_list, 1):
                caller = edge.get("caller_fqn", "")
                callee = edge.get("callee_fqn", "")
                caller_src = edge.get("caller_source", "")
                callee_src = edge.get("callee_source", "")
                count = edge.get("call_count", 0)
                lines.append(f"| {idx} | `{caller}` | `{callee}` | {caller_src} | {callee_src} | {count} |")

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            console.print(f"[green]✅ Markdown berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor Markdown: {e}[/red]")

    def _export_csv(self):
        try:
            if not self.last_edge_list:
                console.print("[yellow]⚠️  Tidak ada data edge untuk diekspor.[/yellow]")
                return

            output_file = CSV_DIR / "phase3_merged.csv"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["source", "target", "call_count", "caller_source", "callee_source", "mode"])
                for edge in self.last_edge_list:
                    writer.writerow([
                        edge.get("caller_fqn", ""),
                        edge.get("callee_fqn", ""),
                        edge.get("call_count", 0),
                        edge.get("caller_source", ""),
                        edge.get("callee_source", ""),
                        edge.get("mode", "static")
                    ])

            console.print(f"[green]✅ CSV berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor CSV: {e}[/red]")

    # ==================== DISPLAY SUMMARY ====================

    def _display_summary(self):
        s = self.last_merge_summary or self.merged_summary
        console.print("\n")
        console.print(Panel.fit(
            "[bold cyan]📊 HASIL FASE 3 - MERGE & FILTER[/bold cyan]",
            border_style="cyan"
        ))

        table = Table(box=box.ROUNDED)
        table.add_column("Metrik", style="bold")
        table.add_column("Nilai", justify="right")

        table.add_row("📦 Total Node", str(s.get("total_nodes", 0)))
        table.add_row("📁 Node Project", str(s.get("project_nodes", 0)))
        table.add_row("📦 Node Eksternal", str(s.get("external_nodes", 0)))
        table.add_row("🔗 Total Edge", str(s.get("total_edges", 0)))
        table.add_row("🔗 Edge Project↔Project", str(s.get("project_edges", 0)))
        table.add_row("🔗 Edge melibatkan Eksternal", str(s.get("external_edges", 0)))
        table.add_row("📂 Sumber data", s.get("source_data", "unknown").capitalize())
        table.add_row("🌐 Sertakan eksternal", "Ya" if s.get("include_external_nodes", True) else "Tidak")
        table.add_row("🔍 Filter edge projek saja", "Ya" if s.get("filter_project_edges_only", False) else "Tidak")

        console.print(table)

    # ==================== MENU UTAMA ====================

    def show_menu(self):
        while True:
            try:
                console.clear()
                console.print(Panel.fit(
                    "[bold cyan]🔗 FASE 3: MERGE & FILTER[/bold cyan]\n"
                    "[dim]Gabungkan data tracing dengan struktur proyek, terapkan filter[/dim]",
                    border_style="cyan"
                ))

                status_source = f"[green]{self.source_type.capitalize()}[/green]" if self.source_type else "[red]Belum dipilih[/red]"
                status_external = "Ya" if self.include_external_nodes else "Tidak"
                status_filter = "Ya" if self.filter_project_edges_only else "Tidak"

                console.print(f"[bold]Status saat ini:[/bold]")
                console.print(f"  📂 Sumber data     : {status_source}")
                console.print(f"  🌐 Sertakan eksternal: {status_external}")
                console.print(f"  🔍 Filter edge projek : {status_filter}")
                console.print("")

                console.print("[bold]Menu:[/bold]")
                console.print("[1] Pilih sumber data (Standard / Advanced)")
                console.print("[2] Ubah 'Sertakan node eksternal' (Ya/Tidak)")
                console.print("[3] Ubah 'Filter edge hanya projek' (Ya/Tidak)")
                console.print("[4] Proses & Ekspor hasil")
                console.print("[0] Kembali ke menu utama (tampilkan ulang)")
                console.print("[x] Keluar dari Fase 3")

                choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "3", "4", "0", "x"])

                if choice == "1":
                    self._select_source()
                elif choice == "2":
                    self._toggle_external()
                elif choice == "3":
                    self._toggle_filter()
                elif choice == "4":
                    self.process()
                elif choice == "0":
                    continue
                elif choice == "x":
                    console.print("[yellow]👋 Keluar dari Fase 3.[/yellow]")
                    sys.exit(0)
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    def _select_source(self):
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]📂 PILIH SUMBER DATA[/bold cyan]",
            border_style="cyan"
        ))

        console.print("[1] Standard Tracing (Statis)")
        console.print("[2] Advanced Tracing (Dinamis)")
        console.print("[0] Batal")

        choice = Prompt.ask("[bold]Pilih sumber[/bold]", choices=["1", "2", "0"])

        if choice == "1":
            if STANDARD_FILE.exists():
                self.source_type = "standard"
                console.print("[green]✅ Sumber data: Standard[/green]")
            else:
                console.print(f"[red]❌ File {STANDARD_FILE} tidak ditemukan.[/red]")
        elif choice == "2":
            if ADVANCED_FILE.exists():
                self.source_type = "advanced"
                console.print("[green]✅ Sumber data: Advanced[/green]")
            else:
                console.print(f"[red]❌ File {ADVANCED_FILE} tidak ditemukan.[/red]")
        else:
            console.print("[dim]Dibatalkan.[/dim]")

        Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    def _toggle_external(self):
        self.include_external_nodes = not self.include_external_nodes
        status = "Ya" if self.include_external_nodes else "Tidak"
        console.print(f"[green]✅ Sertakan node eksternal: {status}[/green]")
        Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    def _toggle_filter(self):
        self.filter_project_edges_only = not self.filter_project_edges_only
        status = "Ya" if self.filter_project_edges_only else "Tidak"
        console.print(f"[green]✅ Filter edge hanya projek: {status}[/green]")
        Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")


def main():
    merger = Phase3Merger()
    merger.show_menu()


if __name__ == "__main__":
    main()