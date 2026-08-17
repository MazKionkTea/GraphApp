#!/usr/bin/env python3
"""
FASE 4: Enrichment (Pengayaan Data)
Menambahkan metrik analisis ke graf hasil Fase 3:
- Fan-in / Fan-out
- LOC (Lines of Code)
- Total Calls & Average Duration
- Entry Point / Leaf Function detection
- Statistik global (avg, max, dll)
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
INPUT_FILE = JSON_DIR / "phase3_merged.json"
if not INPUT_FILE.exists():
    INPUT_FILE = OUTPUT_DIR / "phase3_merged.json"  # fallback

# File output
OUTPUT_FILE = JSON_DIR / "phase4_enriched.json"


class Phase4Enricher:
    def __init__(self):
        # Data dari Fase 3
        self.nodes: List[Dict] = []
        self.edges: List[Dict] = []
        self.summary: Dict = {}

        # Indeks untuk akses cepat
        self.nodes_by_fqn: Dict[str, Dict] = {}
        self.edges_by_caller: Dict[str, List[Dict]] = defaultdict(list)
        self.edges_by_callee: Dict[str, List[Dict]] = defaultdict(list)

        # Hasil enriched
        self.enriched_nodes: List[Dict] = []
        self.enriched_summary: Dict = {}

        # Data untuk ekspor
        self.last_enrich_result: Optional[Dict] = None
        self.last_enrich_summary: Optional[Dict] = None
        self.last_node_list: Optional[List[Dict]] = None
        self.last_edge_list: Optional[List[Dict]] = None

        # Muat data Fase 3
        self._load_phase3()

    # ==================== LOAD DATA ====================

    def _load_phase3(self):
        """Muat data dari Fase 3"""
        if not INPUT_FILE.exists():
            console.print(f"[red]❌ File {INPUT_FILE} tidak ditemukan. Jalankan Fase 3 terlebih dahulu.[/red]")
            console.print("[yellow]Pastikan file ada di: trace_output/json/phase3_merged.json[/yellow]")
            sys.exit(1)

        try:
            with open(INPUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.nodes = data.get("nodes", [])
                self.edges = data.get("edges", [])
                self.summary = data.get("summary", {})
            console.print(f"[green]✅ Data Fase 3 dimuat: {len(self.nodes)} node, {len(self.edges)} edge.[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal membaca {INPUT_FILE}: {e}[/red]")
            sys.exit(1)

    # ==================== PROSES ENRICHMENT ====================

    def process(self):
        """Proses utama: tambahkan metrik ke setiap node"""
        console.print("[cyan]📊 Menambahkan metrik analisis...[/cyan]")

        try:
            # Step 1: Bangun indeks
            for node in self.nodes:
                fqn = node.get("fqn")
                if fqn:
                    self.nodes_by_fqn[fqn] = node

            for edge in self.edges:
                caller = edge.get("caller_fqn")
                callee = edge.get("callee_fqn")
                if caller and callee:
                    self.edges_by_caller[caller].append(edge)
                    self.edges_by_callee[callee].append(edge)

            # Step 2: Enrich setiap node
            self.enriched_nodes = []
            for fqn, node in self.nodes_by_fqn.items():
                enriched = dict(node)

                # Hitung fan-in: jumlah caller unik
                callee_edges = self.edges_by_callee.get(fqn, [])
                caller_set = {e.get("caller_fqn") for e in callee_edges if e.get("caller_fqn")}
                fan_in = len(caller_set)

                # Hitung fan-out: jumlah callee unik
                caller_edges = self.edges_by_caller.get(fqn, [])
                callee_set = {e.get("callee_fqn") for e in caller_edges if e.get("callee_fqn")}
                fan_out = len(callee_set)

                # LOC (Lines of Code)
                line_start = node.get("line_start")
                line_end = node.get("line_end")
                loc = None
                if line_start and line_end:
                    loc = line_end - line_start + 1

                # Total Calls (dari edge sebagai callee)
                total_calls = sum(e.get("call_count", 0) for e in callee_edges)

                # Average Duration (dari edge sebagai callee)
                total_time = sum(e.get("total_time_seconds", 0) for e in callee_edges)
                avg_duration = total_time / total_calls if total_calls > 0 else 0

                # Status
                node_type = node.get("type", "")
                is_entry_point = False
                is_leaf = False
                if node_type in ("function", "method"):
                    is_entry_point = (fan_in == 0)
                    is_leaf = (fan_out == 0)

                # Tambahkan metrik ke node
                enriched["fan_in"] = fan_in
                enriched["fan_out"] = fan_out
                enriched["loc"] = loc
                enriched["total_calls"] = total_calls
                enriched["avg_duration_seconds"] = round(avg_duration, 6)
                enriched["is_entry_point"] = is_entry_point
                enriched["is_leaf"] = is_leaf

                self.enriched_nodes.append(enriched)

            console.print(f"[dim]   → {len(self.enriched_nodes)} node diperkaya.[/dim]")

            # Step 3: Hitung statistik global
            self._compute_global_stats()

            # Peringatan jika tidak ada fungsi/metode
            if self.enriched_summary.get("function_nodes", 0) == 0:
                console.print("[yellow]⚠️  Tidak ada fungsi/metode ditemukan. Metrik fan-in/out tidak dihitung.[/yellow]")

            # Step 4: Simpan hasil ke memori
            self.last_enrich_result = {
                "session_info": {
                    "source_type": self.summary.get("source_data", "unknown"),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "include_external_nodes": self.summary.get("include_external_nodes", True),
                    "filter_project_edges_only": self.summary.get("filter_project_edges_only", False),
                },
                "nodes": self.enriched_nodes,
                "edges": self.edges,
                "summary": self.enriched_summary,
            }
            self.last_node_list = self.enriched_nodes
            self.last_edge_list = self.edges
            self.last_enrich_summary = self.enriched_summary

            console.print("[green]✅ Proses enrichment selesai![/green]")

            # Step 5: Tampilkan ringkasan
            self._display_summary()

            # Step 6: Tampilkan menu pasca-enrichment
            self._show_post_enrich_menu()

        except Exception as e:
            console.print(f"[red]❌ Error saat proses: {e}[/red]")
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
            console.print("[yellow]Silakan perbaiki error di atas, lalu ulangi proses.[/yellow]")
            if self.last_enrich_result:
                console.print("[dim]Data sebagian sudah tersedia, mencoba menampilkan menu...[/dim]")
                self._show_post_enrich_menu()

    def _compute_global_stats(self):
        """Hitung metrik global dari semua node"""
        function_nodes = [n for n in self.enriched_nodes if n.get("type") in ("function", "method")]

        if not function_nodes:
            self.enriched_summary = {
                "total_nodes": len(self.enriched_nodes),
                "function_nodes": 0,
                "avg_fan_in": 0,
                "avg_fan_out": 0,
                "max_fan_in": 0,
                "max_fan_out": 0,
                "entry_points": [],
                "leaf_functions": [],
                "source_summary": self.summary,
            }
            return

        fan_in_values = [n.get("fan_in", 0) for n in function_nodes]
        fan_out_values = [n.get("fan_out", 0) for n in function_nodes]
        total_calls_values = [n.get("total_calls", 0) for n in function_nodes]

        avg_fan_in = sum(fan_in_values) / len(fan_in_values) if fan_in_values else 0
        avg_fan_out = sum(fan_out_values) / len(fan_out_values) if fan_out_values else 0

        max_fan_in_node = max(function_nodes, key=lambda n: n.get("fan_in", 0))
        max_fan_out_node = max(function_nodes, key=lambda n: n.get("fan_out", 0))
        max_total_calls_node = max(function_nodes, key=lambda n: n.get("total_calls", 0))

        entry_points = [n.get("fqn") for n in function_nodes if n.get("is_entry_point", False)]
        leaf_functions = [n.get("fqn") for n in function_nodes if n.get("is_leaf", False)]

        self.enriched_summary = {
            "total_nodes": len(self.enriched_nodes),
            "function_nodes": len(function_nodes),
            "avg_fan_in": round(avg_fan_in, 2),
            "avg_fan_out": round(avg_fan_out, 2),
            "max_fan_in": max_fan_in_node.get("fan_in", 0),
            "max_fan_in_node": max_fan_in_node.get("fqn", ""),
            "max_fan_out": max_fan_out_node.get("fan_out", 0),
            "max_fan_out_node": max_fan_out_node.get("fqn", ""),
            "max_total_calls": max_total_calls_node.get("total_calls", 0),
            "max_total_calls_node": max_total_calls_node.get("fqn", ""),
            "entry_points": entry_points,
            "leaf_functions": leaf_functions,
            "source_summary": self.summary,
        }

    # ==================== MENU PASCA-ENRICH ====================

    def _show_post_enrich_menu(self):
        """Tampilkan menu setelah enrichment selesai dengan opsi ekspor."""
        while True:
            try:
                console.clear()
                console.print(Panel.fit(
                    "[bold green]✅ Proses Enrichment selesai![/bold green]",
                    border_style="green"
                ))

                summary = self.last_enrich_summary or {}
                if summary:
                    console.print(f"[dim]Total node: {summary.get('total_nodes', 0)}[/dim]")
                    console.print(f"[dim]Fungsi/Method: {summary.get('function_nodes', 0)}[/dim]")
                    console.print(f"[dim]Entry points: {len(summary.get('entry_points', []))} | Leaf functions: {len(summary.get('leaf_functions', []))}[/dim]")
                else:
                    console.print("[yellow]⚠️  Tidak ada data untuk ditampilkan. Jalankan proses terlebih dahulu (menu 1).[/yellow]")

                console.print("\n[bold]Pilih tindakan selanjutnya:[/bold]\n")
                console.print(f"[1] Ekspor JSON -> [yellow]{JSON_DIR / 'phase4_enriched.json'}[/yellow]")
                console.print(f"[2] Ekspor XML -> [yellow]{XML_DIR / 'phase4_enriched.xml'}[/yellow]")
                console.print(f"[3] Ekspor DOT -> [yellow]{DOT_DIR / 'phase4_enriched.dot'}[/yellow]")
                console.print(f"[4] Ekspor Markdown -> [yellow]{MD_DIR / 'phase4_enriched.md'}[/yellow]")
                console.print(f"[5] Ekspor CSV -> [yellow]{CSV_DIR / 'phase4_enriched.csv'}[/yellow]")
                console.print("[6] Tampilkan ringkasan (ulang)")
                console.print("[7] Tampilkan daftar entry points (lengkap)")  # BARU
                console.print("[8] Tampilkan daftar leaf functions (lengkap)")  # BARU
                console.print("[0] Kembali ke menu utama Fase 4")
                console.print("[x] Keluar")

                choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "3", "4", "5", "6", "7", "8", "0", "x"])

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
                    self._display_entry_points()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "8":
                    self._display_leaf_functions()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "0":
                    return
                else:  # x
                    console.print("[yellow]👋 Keluar dari Fase 4.[/yellow]")
                    sys.exit(0)
            except Exception as e:
                console.print(f"[red]❌ Error di menu: {e}[/red]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    # ==================== DISPLAY ENTRY POINTS & LEAF FUNCTIONS ====================

    def _display_entry_points(self):
        """Tampilkan daftar entry points lengkap dengan navigasi halaman"""
        summary = self.last_enrich_summary or {}
        entry_points = summary.get("entry_points", [])
        if not entry_points:
            console.print("[yellow]⚠️  Tidak ada entry points ditemukan.[/yellow]")
            return

        self._display_list_with_pagination("Entry Points", entry_points, "🚪")

    def _display_leaf_functions(self):
        """Tampilkan daftar leaf functions lengkap dengan navigasi halaman"""
        summary = self.last_enrich_summary or {}
        leaf_functions = summary.get("leaf_functions", [])
        if not leaf_functions:
            console.print("[yellow]⚠️  Tidak ada leaf functions ditemukan.[/yellow]")
            return

        self._display_list_with_pagination("Leaf Functions", leaf_functions, "🍃")

    def _display_list_with_pagination(self, title: str, items: List[str], icon: str):
        """Generic pagination untuk daftar string"""
        total = len(items)
        page = 0
        page_size = 20
        total_pages = (total - 1) // page_size + 1 if total > 0 else 1

        while True:
            console.clear()
            console.print(Panel.fit(
                f"[bold cyan]{icon} {title} (Halaman {page + 1}/{total_pages})[/bold cyan]",
                border_style="cyan"
            ))

            start = page * page_size
            end = min(start + page_size, total)
            page_items = items[start:end]

            table = Table(box=box.ROUNDED)
            table.add_column("No", style="bold", width=6)
            table.add_column("FQN", style="cyan", no_wrap=True)

            for i, fqn in enumerate(page_items, start=start + 1):
                table.add_row(str(i), fqn)

            console.print(table)

            nav_info = ""
            if page > 0:
                nav_info += "[p] Previous  "
            if page < total_pages - 1:
                nav_info += "[n] Next  "
            nav_info += "[0] Kembali"

            console.print(f"[dim]Navigasi: {nav_info}[/dim]")
            console.print(f"[dim]Total: {total} item[/dim]")

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
            if not self.last_enrich_result:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = JSON_DIR / "phase4_enriched.json"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(self.last_enrich_result, f, indent=2, ensure_ascii=False)

            console.print(f"[green]✅ JSON berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor JSON: {e}[/red]")

    def _export_xml(self):
        try:
            if not self.last_node_list:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = XML_DIR / "phase4_enriched.xml"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            root = ET.Element("enriched_graph")
            session = ET.SubElement(root, "session_info")
            for k, v in (self.last_enrich_result or {}).get("session_info", {}).items():
                e = ET.SubElement(session, k)
                e.text = str(v)

            summary = ET.SubElement(root, "summary")
            # Untuk entry_points dan leaf_functions, simpan sebagai list
            for k, v in (self.last_enrich_summary or {}).items():
                if isinstance(v, list):
                    list_elem = ET.SubElement(summary, k)
                    for item in v:
                        item_elem = ET.SubElement(list_elem, "item")
                        item_elem.text = str(item)
                else:
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
            if not self.last_node_list:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = DOT_DIR / "phase4_enriched.dot"
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
                "digraph EnrichedGraph {",
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
                fan_in = node.get("fan_in", 0)

                if source_type == "external":
                    color = "#eeeeee"
                else:
                    color = type_colors.get(node_type, "#cccccc")

                # Tambahkan fan-in ke label
                if node_type in ("method", "function"):
                    label = f"{label}\\n(fan-in: {fan_in})"

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
            if not self.last_node_list:
                console.print("[yellow]⚠️  Tidak ada data untuk diekspor.[/yellow]")
                return

            output_file = MD_DIR / "phase4_enriched.md"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            lines = []
            lines.append("# Hasil Enrichment (Fase 4)")
            lines.append("")
            lines.append(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            lines.append("## Summary")
            summary = self.last_enrich_summary or {}
            lines.append("| Metrik | Nilai |")
            lines.append("|--------|-------|")
            lines.append(f"| Total Node | {summary.get('total_nodes', 0)} |")
            lines.append(f"| Fungsi/Method | {summary.get('function_nodes', 0)} |")
            lines.append(f"| Rata-rata Fan-in | {summary.get('avg_fan_in', 0)} |")
            lines.append(f"| Rata-rata Fan-out | {summary.get('avg_fan_out', 0)} |")
            lines.append(f"| Max Fan-in ({summary.get('max_fan_in', 0)}) | `{summary.get('max_fan_in_node', '')}` |")
            lines.append(f"| Max Fan-out ({summary.get('max_fan_out', 0)}) | `{summary.get('max_fan_out_node', '')}` |")
            lines.append(f"| Max Total Calls ({summary.get('max_total_calls', 0)}) | `{summary.get('max_total_calls_node', '')}` |")
            lines.append(f"| Entry Points (fan-in=0) | {len(summary.get('entry_points', []))} |")
            lines.append(f"| Leaf Functions (fan-out=0) | {len(summary.get('leaf_functions', []))} |")
            lines.append("")
            lines.append("## Entry Points (SEMUA)")
            for ep in summary.get('entry_points', []):
                lines.append(f"- `{ep}`")
            lines.append("")
            lines.append("## Leaf Functions (SEMUA)")
            for lf in summary.get('leaf_functions', []):
                lines.append(f"- `{lf}`")
            lines.append("")
            lines.append("## Nodes (10 pertama)")
            lines.append("| FQN | Type | Fan-in | Fan-out | Total Calls | Entry Point | Leaf |")
            lines.append("|-----|------|--------|---------|-------------|-------------|------|")
            for node in self.last_node_list[:10]:
                fqn = node.get("fqn", "")
                typ = node.get("type", "")
                fan_in = node.get("fan_in", 0)
                fan_out = node.get("fan_out", 0)
                total_calls = node.get("total_calls", 0)
                is_entry = "✅" if node.get("is_entry_point", False) else "❌"
                is_leaf = "✅" if node.get("is_leaf", False) else "❌"
                lines.append(f"| `{fqn}` | {typ} | {fan_in} | {fan_out} | {total_calls} | {is_entry} | {is_leaf} |")

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            console.print(f"[green]✅ Markdown berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor Markdown: {e}[/red]")

    def _export_csv(self):
        try:
            if not self.last_node_list:
                console.print("[yellow]⚠️  Tidak ada data node untuk diekspor.[/yellow]")
                return

            output_file = CSV_DIR / "phase4_enriched.csv"
            if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
                return

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["fqn", "name", "type", "source_type", "fan_in", "fan_out", "total_calls", "loc", "is_entry_point", "is_leaf"])
                for node in self.last_node_list:
                    writer.writerow([
                        node.get("fqn", ""),
                        node.get("name", ""),
                        node.get("type", ""),
                        node.get("source_type", ""),
                        node.get("fan_in", 0),
                        node.get("fan_out", 0),
                        node.get("total_calls", 0),
                        node.get("loc", ""),
                        node.get("is_entry_point", False),
                        node.get("is_leaf", False)
                    ])

            console.print(f"[green]✅ CSV berhasil diekspor ke {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Gagal ekspor CSV: {e}[/red]")

    # ==================== DISPLAY SUMMARY ====================

    def _display_summary(self):
        """Tampilkan ringkasan hasil di layar"""
        s = self.last_enrich_summary or self.enriched_summary
        console.print("\n")
        console.print(Panel.fit(
            "[bold magenta]📊 HASIL FASE 4 - ENRICHMENT[/bold magenta]",
            border_style="magenta"
        ))

        table = Table(box=box.ROUNDED)
        table.add_column("Metrik", style="bold")
        table.add_column("Nilai", justify="right")

        table.add_row("📦 Total Node", str(s.get("total_nodes", 0)))
        table.add_row("🔧 Fungsi/Method", str(s.get("function_nodes", 0)))
        table.add_row("📊 Rata-rata Fan-in", str(s.get("avg_fan_in", 0)))
        table.add_row("📊 Rata-rata Fan-out", str(s.get("avg_fan_out", 0)))

        max_fan_in = s.get("max_fan_in", 0)
        max_fan_in_node = s.get("max_fan_in_node", "")
        table.add_row(f"📈 Max Fan-in ({max_fan_in})", max_fan_in_node[:40] + "..." if len(max_fan_in_node) > 40 else max_fan_in_node)

        max_fan_out = s.get("max_fan_out", 0)
        max_fan_out_node = s.get("max_fan_out_node", "")
        table.add_row(f"📈 Max Fan-out ({max_fan_out})", max_fan_out_node[:40] + "..." if len(max_fan_out_node) > 40 else max_fan_out_node)

        max_calls = s.get("max_total_calls", 0)
        max_calls_node = s.get("max_total_calls_node", "")
        table.add_row(f"📞 Max Total Calls ({max_calls})", max_calls_node[:40] + "..." if len(max_calls_node) > 40 else max_calls_node)

        entry_count = len(s.get("entry_points", []))
        leaf_count = len(s.get("leaf_functions", []))
        table.add_row("🚪 Entry Points (fan-in=0)", str(entry_count))
        table.add_row("🍃 Leaf Functions (fan-out=0)", str(leaf_count))

        console.print(table)

        # Tampilkan 5 entry points pertama (sebagai preview)
        if entry_count > 0:
            console.print("\n[bold cyan]🚪 Entry Points (5 pertama dari total {entry_count}):[/bold cyan]")
            for fqn in s.get("entry_points", [])[:5]:
                console.print(f"  • {fqn}")

        # Tampilkan 5 leaf functions pertama (sebagai preview)
        if leaf_count > 0:
            console.print("\n[bold green]🍃 Leaf Functions (5 pertama dari total {leaf_count}):[/bold green]")
            for fqn in s.get("leaf_functions", [])[:5]:
                console.print(f"  • {fqn}")

    # ==================== MENU UTAMA ====================

    def show_menu(self):
        while True:
            try:
                console.clear()
                console.print(Panel.fit(
                    "[bold magenta]📈 FASE 4: ENRICHMENT[/bold magenta]\n"
                    "[dim]Tambahkan metrik analisis ke graf hasil Fase 3[/dim]",
                    border_style="magenta"
                ))

                # Tampilkan status file input
                if INPUT_FILE.exists():
                    console.print(f"[green]✅ Input file: {INPUT_FILE}[/green]")
                else:
                    console.print(f"[red]❌ Input file: {INPUT_FILE} tidak ditemukan.[/red]")

                if OUTPUT_FILE.exists():
                    console.print(f"[dim]Output file: {OUTPUT_FILE} (sudah ada)[/dim]")
                else:
                    console.print(f"[dim]Output file: {OUTPUT_FILE} (akan dibuat)[/dim]")

                console.print("\n[bold]Menu:[/bold]")
                console.print("[1] Proses Enrichment")
                console.print("[2] Tampilkan ringkasan hasil (jika sudah ada)")
                console.print("[0] Kembali ke menu utama")
                console.print("[x] Keluar dari Fase 4")

                choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "0", "x"])

                if choice == "1":
                    self.process()
                elif choice == "2":
                    self._display_stored_result()
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
                elif choice == "0":
                    continue
                else:  # x
                    console.print("[yellow]👋 Keluar dari Fase 4.[/yellow]")
                    sys.exit(0)
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    def _display_stored_result(self):
        """Tampilkan ringkasan dari file output yang sudah ada"""
        if not OUTPUT_FILE.exists():
            console.print(f"[yellow]⚠️  File {OUTPUT_FILE} belum ada. Jalankan proses terlebih dahulu (menu 1).[/yellow]")
            return

        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                summary = data.get("summary", {})
                nodes = data.get("nodes", [])

            console.print("\n")
            console.print(Panel.fit(
                "[bold magenta]📊 HASIL FASE 4 (dari file)[/bold magenta]",
                border_style="magenta"
            ))

            table = Table(box=box.ROUNDED)
            table.add_column("Metrik", style="bold")
            table.add_column("Nilai", justify="right")

            table.add_row("📦 Total Node", str(summary.get("total_nodes", 0)))
            table.add_row("🔧 Fungsi/Method", str(summary.get("function_nodes", 0)))
            table.add_row("📊 Rata-rata Fan-in", str(summary.get("avg_fan_in", 0)))
            table.add_row("📊 Rata-rata Fan-out", str(summary.get("avg_fan_out", 0)))
            table.add_row("🚪 Entry Points", str(len(summary.get("entry_points", []))))
            table.add_row("🍃 Leaf Functions", str(len(summary.get("leaf_functions", []))))

            console.print(table)

            # Tampilkan contoh node pertama
            if nodes:
                console.print("\n[bold]📝 Contoh node (pertama):[/bold]")
                first = nodes[0]
                console.print(f"  FQN       : {first.get('fqn', '')}")
                console.print(f"  Fan-in    : {first.get('fan_in', 0)}")
                console.print(f"  Fan-out   : {first.get('fan_out', 0)}")
                console.print(f"  Total Calls: {first.get('total_calls', 0)}")
                console.print(f"  Entry Point: {'Ya' if first.get('is_entry_point', False) else 'Tidak'}")
                console.print(f"  Leaf      : {'Ya' if first.get('is_leaf', False) else 'Tidak'}")

        except Exception as e:
            console.print(f"[red]❌ Gagal membaca {OUTPUT_FILE}: {e}[/red]")


def main():
    enricher = Phase4Enricher()
    enricher.show_menu()


if __name__ == "__main__":
    main()
