#!/usr/bin/env python3
"""
FASE 2: Function Tracing
Mode 1: Standard (Statis) - Analisis AST tanpa eksekusi (default)
Mode 2: Advanced (Dinamis) - Eksekusi di terminal baru dengan sys.settrace
"""

import os
import sys
import json
import ast
import time
import shutil
import subprocess
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import box

console = Console()


class Phase2Tracer:
    """Fase 2: Tracing pemanggilan fungsi (statis & dinamis)"""

    def __init__(self):
        self.project_root: Optional[Path] = None
        self.py_files: List[Path] = []
        self.current_page: int = 0
        self.page_size: int = 15
        self.target_script: Optional[Path] = None

        # Folder output utama
        self.output_dir = Path("trace_output")
        self.output_dir.mkdir(exist_ok=True)

        # Subfolder untuk setiap format
        self.json_dir = self.output_dir / "json"
        self.xml_dir = self.output_dir / "xml"
        self.dot_dir = self.output_dir / "dot"
        self.md_dir = self.output_dir / "md"
        self.csv_dir = self.output_dir / "csv"
        for d in [self.json_dir, self.xml_dir, self.dot_dir, self.md_dir, self.csv_dir]:
            d.mkdir(exist_ok=True)

        # Data hasil tracing
        self.last_trace_result: Optional[Dict] = None
        self.last_trace_mode: Optional[str] = None
        self.last_trace_summary: Optional[Dict] = None
        self.last_edge_list: Optional[List[Dict]] = None

        # Setelan default
        self.settings = {
            "mode": "standard",          # "standard" atau "advanced"
            "show_call_count": False,    # default OFF
        }

        self._load_phase1_data()

    # ==================== LOAD PHASE 1 ====================

    def _load_phase1_data(self):
        """Baca hasil Phase 1 jika ada"""
        phase1_file = self.output_dir / "phase1_static_map.json"
        if phase1_file.exists():
            try:
                with open(phase1_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "project_root" in data:
                        self.project_root = Path(data["project_root"])
                        console.print(f"[green]✅ Membaca direktori dari Phase 1: {self.project_root}[/green]")
                        self._scan_py_files()
            except Exception:
                pass
        else:
            console.print("[yellow]⚠️  File Phase 1 tidak ditemukan. Pilih direktori manual (menu 0).[/yellow]")

    def _scan_py_files(self):
        """Scan semua file .py di project_root"""
        if self.project_root and self.project_root.is_dir():
            self.py_files = list(self.project_root.rglob("*.py"))
            self.py_files = [
                f for f in self.py_files
                if f.name != "__init__.py" and "__pycache__" not in str(f)
            ]
            self.py_files.sort()

    # ==================== UTILITY ====================

    def _get_source_type(self, file_path: Path) -> str:
        if self.project_root is None:
            return "external"
        try:
            file_path.relative_to(self.project_root)
            return "project"
        except ValueError:
            return "external"

    def _get_module_name(self, file_path: Path) -> str:
        if self.project_root:
            try:
                rel_path = file_path.relative_to(self.project_root)
                parts = list(rel_path.parts)
                parts[-1] = parts[-1].replace(".py", "")
                return ".".join(parts)
            except ValueError:
                pass
        return file_path.stem

    def _get_terminal_cmd(self) -> Optional[List[str]]:
        terminals = [
            ("gnome-terminal", ["gnome-terminal", "--"]),
            ("konsole", ["konsole", "-e"]),
            ("xterm", ["xterm", "-e"]),
            ("lxterminal", ["lxterminal", "-e"]),
            ("terminator", ["terminator", "-x"]),
        ]
        for name, cmd in terminals:
            if shutil.which(name):
                return cmd
        return None

    # ==================== MENU UTAMA ====================

    def show_menu(self):
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold cyan]🔍 PHASE 2: FUNCTION TRACING[/bold cyan]\n"
                "[dim]Analisis pemanggilan fungsi antar Package/Modul/Class/Method[/dim]",
                border_style="cyan"
            ))

            status_dir = f"[green]{self.project_root}[/green]" if self.project_root else "[red]Belum dipilih[/red]"
            status_files = f"{len(self.py_files)} file .py" if self.py_files else "0 file"
            status_target = f"[green]{self.target_script.name}[/green]" if self.target_script else "[red]Belum dipilih[/red]"

            info_table = Table(box=box.MINIMAL, show_header=False)
            info_table.add_row("📂 Direktori aktif", status_dir)
            info_table.add_row("📄 File ditemukan", status_files)
            info_table.add_row("🎯 Target terpilih", status_target)
            console.print(info_table)

            mode_label = "Statis" if self.settings["mode"] == "standard" else "Dinamis"
            call_label = "Ya" if self.settings["show_call_count"] else "Tidak"
            console.print(f"[dim]Mode: {mode_label} | Tampilkan call_count: {call_label}[/dim]")

            console.print("\n[bold]Menu:[/bold]")
            console.print("[1] Jalankan Tracing")
            console.print("[2] Setelan")
            console.print("[0] Pilih direktori / scan ulang")
            console.print("[x] Keluar")

            choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "0", "x"])

            if choice == "1":
                self._run_tracing()
            elif choice == "2":
                self._settings_menu()
            elif choice == "0":
                self._select_directory()
            elif choice == "x":
                console.print("[yellow]👋 Keluar dari Phase 2.[/yellow]")
                break

    # ==================== SETELAN ====================

    def _settings_menu(self):
        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold yellow]⚙️  SETELAN[/bold yellow]",
                border_style="yellow"
            ))

            mode_label = "Dinamis" if self.settings["mode"] == "advanced" else "Statis"
            call_label = "Ya" if self.settings["show_call_count"] else "Tidak"

            console.print("\n[bold]Status saat ini:[/bold]")
            console.print(f"  [1] Mode Tracing: [cyan]{mode_label}[/cyan]")
            console.print(f"  [2] Tampilkan call_count: [cyan]{call_label}[/cyan]")
            console.print("")
            console.print("[1] Ubah Mode Tracing (Statis ↔ Dinamis)")
            console.print("[2] Ubah Tampilkan call_count (Ya ↔ Tidak)")
            console.print("[0] Kembali")

            choice = Prompt.ask("[bold]Pilih opsi[/bold]", choices=["1", "2", "0"])

            if choice == "1":
                self.settings["mode"] = "advanced" if self.settings["mode"] == "standard" else "standard"
                console.print(f"[green]✅ Mode berubah: {self.settings['mode'].capitalize()}[/green]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            elif choice == "2":
                self.settings["show_call_count"] = not self.settings["show_call_count"]
                console.print(f"[green]✅ Tampilkan call_count: {'Ya' if self.settings['show_call_count'] else 'Tidak'}[/green]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            elif choice == "0":
                return

    # ==================== PILIH DIREKTORI & TARGET ====================

    def _select_directory(self):
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]📂 PILIH DIREKTORI PROYEK[/bold cyan]",
            border_style="cyan"
        ))

        if self.project_root:
            if Confirm.ask(f"[dim]Gunakan direktori dari Phase 1: {self.project_root}?[/dim]", default=True):
                self._scan_py_files()
                console.print(f"[green]✅ {len(self.py_files)} file .py ditemukan.[/green]")
                Prompt.ask("[dim]Tekan Enter untuk kembali[/dim]", default="")
                return

        while True:
            path_input = Prompt.ask("[bold]Masukkan path direktori proyek[/bold]")
            if not path_input.strip():
                console.print("[red]Path tidak boleh kosong.[/red]")
                continue

            test_path = Path(path_input).resolve()
            if test_path.is_dir():
                self.project_root = test_path
                self._scan_py_files()
                console.print(f"[green]✅ {len(self.py_files)} file .py ditemukan di {self.project_root}[/green]")
                Prompt.ask("[dim]Tekan Enter untuk kembali[/dim]", default="")
                return
            else:
                console.print(f"[red]❌ Direktori tidak ditemukan: {path_input}[/red]")
                choice = Prompt.ask(
                    "[bold]Pilih opsi[/bold]",
                    choices=["1", "2", "x"],
                    default="1"
                )
                if choice == "1":
                    continue
                elif choice == "2":
                    self.project_root = test_path
                    self.py_files = []
                    console.print("[yellow]⚠️  Direktori tidak valid, tetapi dilanjutkan dengan 0 file.[/yellow]")
                    Prompt.ask("[dim]Tekan Enter untuk kembali[/dim]", default="")
                    return
                else:
                    return

    def _select_target_script(self) -> bool:
        if not self.py_files:
            console.print("[yellow]⚠️  Tidak ada file .py. Pilih direktori terlebih dahulu (menu 0).[/yellow]")
            Prompt.ask("[dim]Tekan Enter untuk kembali[/dim]", default="")
            return False

        total_pages = (len(self.py_files) - 1) // self.page_size + 1

        while True:
            console.clear()
            console.print(Panel.fit(
                f"[bold]📂 Pilih script target (Halaman {self.current_page + 1}/{total_pages})[/bold]\n"
                f"[dim]Direktori: {self.project_root}[/dim]",
                border_style="cyan"
            ))

            start_idx = self.current_page * self.page_size
            end_idx = min(start_idx + self.page_size, len(self.py_files))
            page_files = self.py_files[start_idx:end_idx]

            table = Table(box=box.MINIMAL)
            table.add_column("No", style="bold", width=6)
            table.add_column("File Path", style="cyan")

            for i, file_path in enumerate(page_files, start=1):
                rel_path = file_path.relative_to(self.project_root) if self.project_root else file_path
                prefix = "▶ " if self.target_script == file_path else "  "
                table.add_row(f"{prefix}{i}", str(rel_path))

            console.print(table)

            nav_parts = []
            if self.current_page > 0:
                nav_parts.append("[p] Previous page")
            if self.current_page < total_pages - 1:
                nav_parts.append("[n] Next page")
            nav_parts.append("[0] Kembali")
            nav_parts.append("[x] Keluar")

            nav_text = "  ".join(nav_parts)
            if self.current_page == 0 and total_pages == 1:
                nav_text += "  [dim](Hanya 1 halaman)[/dim]"
            else:
                nav_text += "\n[dim](Hanya tersedia jika ada halaman sebelumnya/berikutnya)[/dim]"

            console.print(Panel(
                nav_text,
                title="[bold]📌 Navigasi[/bold]",
                border_style="cyan"
            ))

            console.print(f"[dim]Pilih nomor file (1-{len(page_files)}) untuk memilih target.[/dim]")

            choice = Prompt.ask("[bold]Pilih opsi / nomor file[/bold]")

            if choice.lower() == 'n':
                if self.current_page < total_pages - 1:
                    self.current_page += 1
                continue
            elif choice.lower() == 'p':
                if self.current_page > 0:
                    self.current_page -= 1
                continue
            elif choice == '0':
                return False
            elif choice.lower() == 'x':
                return False

            try:
                num = int(choice)
                if 1 <= num <= len(page_files):
                    self.target_script = page_files[num - 1]
                    console.print(f"[green]✅ Target dipilih: {self.target_script.name}[/green]")
                    return True
                else:
                    console.print(f"[red]❌ Nomor tidak valid. Pilih 1-{len(page_files)}.[/red]")
                    Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            except ValueError:
                console.print("[red]❌ Masukkan nomor atau opsi navigasi yang valid.[/red]")
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")

    # ==================== JALANKAN TRACING ====================

    def _run_tracing(self):
        """Jalankan tracing dengan mode dari setelan"""
        if not self.target_script:
            console.print("[yellow]⚠️  Belum ada target script. Pilih target terlebih dahulu.[/yellow]")
            if not self._select_target_script():
                return

        if not self.project_root:
            console.print("[red]❌ Project root belum ditentukan. Pilih direktori dulu (menu 0).[/red]")
            return

        if self.settings["mode"] == "standard":
            self._run_standard_tracing()
        else:
            self._run_advanced_tracing()

        if self.last_edge_list is not None:
            self._show_post_trace_menu()

    # ==================== STANDARD TRACING ====================

    def _run_standard_tracing(self):
        """Eksekusi Standard Tracing - hasil disimpan di memori"""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]📊 STANDARD TRACING (STATIS)[/bold cyan]",
            border_style="cyan"
        ))
        console.print(f"[dim]Menganalisis: {self.target_script}[/dim]")
        console.print("[dim]Mencari semua pemanggilan fungsi...[/dim]")

        all_calls = []

        class CallCollector(ast.NodeVisitor):
            def __init__(self, module_name: str):
                self.module_name = module_name
                self.class_stack = []
                self.function_stack = []
                self.calls = []

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

                if isinstance(node.func, ast.Name):
                    callee_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    attr = node.func.attr
                    if isinstance(node.func.value, ast.Name):
                        callee_name = f"{node.func.value.id}.{attr}"
                    else:
                        callee_name = attr
                else:
                    callee_name = "unknown"

                self.calls.append({
                    "caller_fqn": caller,
                    "callee_fqn": callee_name or "unknown",
                    "line_number": node.lineno,
                })
                self.generic_visit(node)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Memproses AST...", total=len(self.py_files))

            if not self.py_files:
                self._scan_py_files()

            for file_path in self.py_files:
                progress.update(task, description=f"[cyan]Menganalisis {file_path.name}")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    tree = ast.parse(content, filename=str(file_path))
                except (SyntaxError, UnicodeDecodeError):
                    progress.advance(task)
                    continue

                module_name = self._get_module_name(file_path)
                collector = CallCollector(module_name)
                collector.visit(tree)

                file_source_type = self._get_source_type(file_path)

                for call in collector.calls:
                    callee_source = "project"
                    callee_fqn = call["callee_fqn"]

                    if callee_fqn and ('.' in callee_fqn or callee_fqn.startswith('_')):
                        parts = callee_fqn.split('.')
                        if parts:
                            mod_name = parts[0]
                            is_project_module = any(p.stem == mod_name for p in self.py_files)
                            if not is_project_module and self.project_root:
                                is_project_module = (self.project_root / f"{mod_name}.py").exists() or (self.project_root / mod_name).is_dir()
                            if not is_project_module:
                                callee_source = "external"
                    else:
                        callee_source = file_source_type

                    all_calls.append({
                        "caller_fqn": call["caller_fqn"],
                        "callee_fqn": callee_fqn,
                        "source_type": callee_source,
                        "file_path": str(file_path),
                        "line_number": call["line_number"],
                    })
                progress.advance(task)

        # Agregasi
        edge_map = defaultdict(lambda: {"call_count": 0, "source_type": "project"})
        for call in all_calls:
            key = (call["caller_fqn"], call["callee_fqn"])
            edge_map[key]["call_count"] += 1
            st = call.get("source_type")
            if st and st in ("project", "external"):
                edge_map[key]["source_type"] = st
            else:
                # Jika masih kosong, tentukan berdasarkan callee
                callee_fqn = call["callee_fqn"]
                if callee_fqn and '.' in callee_fqn:
                    mod_name = callee_fqn.split('.')[0]
                    is_project = any(p.stem == mod_name for p in self.py_files)
                    edge_map[key]["source_type"] = "project" if is_project else "external"
                else:
                    edge_map[key]["source_type"] = "project"

        edge_list = []
        for (caller, callee), data in edge_map.items():
            edge_list.append({
                "caller_fqn": caller,
                "callee_fqn": callee,
                "call_count": data["call_count"],
                "source_type": data.get("source_type", "project"),
                "mode": "static"
            })

        self.last_trace_mode = "standard"
        self.last_edge_list = edge_list
        self.last_trace_result = {
            "session_info": {
                "mode": "standard",
                "target_script": str(self.target_script),
                "project_root": str(self.project_root),
                "total_edges": len(edge_list),
                "total_files_scanned": len(self.py_files),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        self.last_trace_summary = {
            "total_edges": len(edge_list),
            "project_edges": sum(1 for e in edge_list if e["source_type"] == "project"),
            "external_edges": sum(1 for e in edge_list if e["source_type"] == "external"),
        }

        self._display_summary()

    # ==================== ADVANCED TRACING ====================

    def _run_advanced_tracing(self):
        """Eksekusi Advanced Tracing (dinamis)"""
        console.clear()
        console.print(Panel.fit(
            "[bold magenta]🚀 ADVANCED TRACING (DINAMIS)[/bold magenta]",
            border_style="magenta"
        ))

        terminal_cmd = self._get_terminal_cmd()
        if not terminal_cmd:
            console.print("[red]❌ Tidak ditemukan terminal emulator (gnome-terminal, konsole, xterm).[/red]")
            console.print("[yellow]Fallback: Menjalankan di background tanpa terminal baru.[/yellow]")
            if Confirm.ask("[bold]Lanjutkan dengan background mode?[/bold]", default=False):
                self._run_dynamic_background()
            return

        self._run_dynamic_terminal(terminal_cmd)

        output_file = self.output_dir / "phase2_advanced_graph.json"
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.last_trace_mode = "advanced"
                self.last_edge_list = data.get("edges", [])
                self.last_trace_result = {
                    "session_info": data.get("session_info", {})
                }
                self.last_trace_summary = data.get("summary", {
                    "total_edges": len(self.last_edge_list),
                    "project_edges": sum(1 for e in self.last_edge_list if e.get("source_type") == "project"),
                    "external_edges": sum(1 for e in self.last_edge_list if e.get("source_type") == "external"),
                })
                self._display_summary()
                output_file.unlink()
            except Exception as e:
                console.print(f"[red]❌ Gagal membaca hasil tracing: {e}[/red]")
                self.last_edge_list = None
        else:
            console.print("[red]❌ File hasil tracing tidak ditemukan.[/red]")
            self.last_edge_list = None

    def _run_dynamic_terminal(self, terminal_cmd: List[str]):
        runner_code = self._generate_runner_script()
        runner_path = self.output_dir / "_phase2_runner.py"

        try:
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(runner_code)

            cmd = terminal_cmd + ["python", str(runner_path), str(self.target_script), str(self.project_root), str(self.output_dir)]
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd=self.project_root
            )
            console.print(f"[green]✅ Terminal baru dibuka untuk menjalankan: {self.target_script.name}[/green]")
            console.print("[dim]Tracer akan berjalan di terminal tersebut.[/dim]")
            console.print("[dim]Tutup terminal target untuk menghentikan tracer.[/dim]")
            console.print("[yellow]⚠️  Jangan tutup terminal utama ini.[/yellow]")
            console.print(f"[dim]Hasil sementara akan disimpan di: {self.output_dir / 'phase2_advanced_graph.json'}[/dim]")

            console.print("\n[bold]Tracing berjalan di terminal terpisah.[/bold]")
            console.print("[dim]Setelah terminal target ditutup, hasil akan dibaca dan ditampilkan.[/dim]")
            Prompt.ask("[dim]Tekan Enter setelah terminal target ditutup untuk melanjutkan...[/dim]", default="")

            if runner_path.exists():
                runner_path.unlink()

        except Exception as e:
            console.print(f"[red]❌ Gagal membuka terminal: {e}[/red]")
            if runner_path.exists():
                runner_path.unlink()

    def _run_dynamic_background(self):
        runner_code = self._generate_runner_script()
        runner_path = self.output_dir / "_phase2_runner.py"

        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(runner_code)

        console.print("[cyan]Menjalankan tracing di background...[/cyan]")
        try:
            process = subprocess.Popen(
                ["python", str(runner_path), str(self.target_script), str(self.project_root), str(self.output_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd=self.project_root
            )
            console.print(f"[green]✅ Tracing berjalan di background (PID: {process.pid})[/green]")
            console.print("[dim]Tracer akan berhenti ketika script target selesai.[/dim]")
            console.print(f"[dim]Hasil sementara akan disimpan di: {self.output_dir / 'phase2_advanced_graph.json'}[/dim]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[magenta]Menunggu tracing selesai...", total=None)
                while process.poll() is None:
                    time.sleep(1)
                progress.update(task, description="[green]✅ Tracing selesai![/green]")

            if runner_path.exists():
                runner_path.unlink()

        except Exception as e:
            console.print(f"[red]❌ Gagal menjalankan tracing: {e}[/red]")

    def _generate_runner_script(self) -> str:
        return '''
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Set, Tuple

class DynamicTracer:
    def __init__(self, project_root: Path, output_dir: Path):
        self.project_root = project_root
        self.output_dir = output_dir
        self.edges: Dict[Tuple[str, str], Dict] = {}
        self.function_stack = []
        self.call_count = 0
        self.return_count = 0
        self.unique_callers = set()
        self.unique_callees = set()
        self.start_time = 0.0
        self.end_time = 0.0
        self.target_script = None

    def _get_module_name(self, frame):
        module = frame.f_globals.get('__name__', '__main__')
        if module == '__main__':
            file_path = frame.f_code.co_filename
            if file_path:
                return Path(file_path).stem
        return module

    def _get_function_qualname(self, frame):
        if hasattr(frame.f_code, 'co_qualname'):
            qualname = frame.f_code.co_qualname
            if qualname != frame.f_code.co_name:
                return qualname
        func_name = frame.f_code.co_name
        if 'self' in frame.f_locals:
            self_obj = frame.f_locals['self']
            if hasattr(self_obj, '__class__'):
                return f"{self_obj.__class__.__name__}.{func_name}"
        elif 'cls' in frame.f_locals:
            cls_obj = frame.f_locals['cls']
            if hasattr(cls_obj, '__name__'):
                return f"{cls_obj.__name__}.{func_name}"
        return func_name

    def _get_fqn(self, frame):
        module = self._get_module_name(frame)
        qualname = self._get_function_qualname(frame)
        return f"{module}.{qualname}"

    def _get_source_type(self, frame):
        code = frame.f_code
        if not code.co_filename:
            return "external"
        file_path = Path(code.co_filename)
        try:
            file_path.relative_to(self.project_root)
            return "project"
        except ValueError:
            return "external"

    def _should_trace(self, frame):
        code = frame.f_code
        if not code.co_filename:
            return False
        if code.co_name in ['_trace_calls', '_trace_returns']:
            return False
        return True

    def _trace_calls(self, frame, event, arg):
        if event != 'call':
            return self._trace_calls
        if not self._should_trace(frame):
            return self._trace_calls

        callee_fqn = self._get_fqn(frame)
        caller_frame = frame.f_back
        if caller_frame and self._should_trace(caller_frame):
            caller_fqn = self._get_fqn(caller_frame)
        else:
            caller_fqn = f"__main__.{Path(self.target_script).stem}"

        start_time = time.perf_counter()
        self.function_stack.append({
            'caller_fqn': caller_fqn,
            'callee_fqn': callee_fqn,
            'start_time': start_time,
            'frame': frame
        })
        self.call_count += 1
        self.unique_callees.add(callee_fqn)
        self.unique_callers.add(caller_fqn)
        return self._trace_calls

    def _trace_returns(self, frame, event, arg):
        if event not in ('return', 'exception'):
            return self._trace_returns
        if not self._should_trace(frame):
            return self._trace_returns
        if not self.function_stack:
            return self._trace_returns

        stack_item = self.function_stack.pop()
        callee_fqn = stack_item['callee_fqn']
        caller_fqn = stack_item['caller_fqn']
        start_time = stack_item['start_time']
        duration = time.perf_counter() - start_time

        self.return_count += 1

        edge_key = (caller_fqn, callee_fqn)
        if edge_key not in self.edges:
            source_type = self._get_source_type(frame)
            self.edges[edge_key] = {
                'caller_fqn': caller_fqn,
                'callee_fqn': callee_fqn,
                'call_count': 0,
                'total_time_seconds': 0.0,
                'max_time_seconds': 0.0,
                'min_time_seconds': float('inf'),
                'source_type': source_type
            }

        edge = self.edges[edge_key]
        edge['call_count'] += 1
        edge['total_time_seconds'] += duration
        if duration > edge['max_time_seconds']:
            edge['max_time_seconds'] = duration
        if duration < edge['min_time_seconds']:
            edge['min_time_seconds'] = duration
        return self._trace_returns

    def run(self, target_script: Path):
        self.target_script = target_script
        self.start_time = time.perf_counter()

        sys.settrace(self._trace_calls)

        original_argv = sys.argv.copy()
        sys.argv = [str(target_script)]

        try:
            import runpy
            runpy.run_path(str(target_script), run_name="__main__")
        except SystemExit:
            pass
        except Exception:
            pass
        finally:
            sys.settrace(None)
            sys.argv = original_argv

        self.end_time = time.perf_counter()
        return self.end_time - self.start_time

    def export_json(self):
        output_path = self.output_dir / "phase2_advanced_graph.json"
        edge_list = []
        for edge_key, edge_data in self.edges.items():
            edge_list.append({
                'caller_fqn': edge_data['caller_fqn'],
                'callee_fqn': edge_data['callee_fqn'],
                'call_count': edge_data['call_count'],
                'total_time_seconds': round(edge_data['total_time_seconds'], 6),
                'avg_time_seconds': round(edge_data['total_time_seconds'] / edge_data['call_count'], 6),
                'max_time_seconds': round(edge_data['max_time_seconds'], 6),
                'min_time_seconds': round(edge_data['min_time_seconds'] if edge_data['min_time_seconds'] != float('inf') else 0, 6),
                'source_type': edge_data['source_type'],
                'mode': 'dynamic'
            })

        edge_list.sort(key=lambda x: x['call_count'], reverse=True)

        data = {
            "session_info": {
                "mode": "advanced",
                "target_script": str(self.target_script),
                "project_root": str(self.project_root),
                "total_calls": self.call_count,
                "total_returns": self.return_count,
                "total_edges": len(self.edges),
                "unique_callers": len(self.unique_callers),
                "unique_callees": len(self.unique_callees),
                "duration_seconds": round(self.end_time - self.start_time, 6)
            },
            "edges": edge_list,
            "unique_functions": sorted(list(self.unique_callers | self.unique_callees)),
            "summary": {
                "total_edges": len(edge_list),
                "project_edges": sum(1 for e in edge_list if e["source_type"] == "project"),
                "external_edges": sum(1 for e in edge_list if e["source_type"] == "external"),
            }
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python runner.py <target_script> <project_root> <output_dir>")
        sys.exit(1)

    target_script = Path(sys.argv[1])
    project_root = Path(sys.argv[2])
    output_dir = Path(sys.argv[3])

    if not target_script.exists():
        print(f"Target script not found: {target_script}")
        sys.exit(1)

    tracer = DynamicTracer(project_root, output_dir)
    tracer.run(target_script)
    tracer.export_json()

    print(f"✅ Tracing selesai. Hasil disimpan di {output_dir / 'phase2_advanced_graph.json'}")
'''

    # ==================== DISPLAY SUMMARY ====================

    def _display_summary(self):
        """Tampilkan ringkasan minimal (tanpa Top 5)"""
        console.print("\n")
        console.print(Panel.fit(
            f"[bold cyan]📊 Hasil {self.last_trace_mode.capitalize()} Tracing[/bold cyan]",
            border_style="cyan"
        ))

        summary = self.last_trace_summary or {}
        table = Table(box=box.ROUNDED)
        table.add_column("Metrik", style="bold")
        table.add_column("Nilai", justify="right")

        table.add_row("📌 Total Edge (pemanggilan unik)", str(summary.get("total_edges", 0)))
        table.add_row("📁 Edge dari Project", str(summary.get("project_edges", 0)))
        table.add_row("📦 Edge ke Library Eksternal", str(summary.get("external_edges", 0)))
        table.add_row("📄 File dianalisis", str(len(self.py_files)))

        console.print(table)

    # ==================== MENU PASCA-TRACING ====================

    def _show_post_trace_menu(self):
        while True:
            console.clear()
            console.print(Panel.fit(
                f"[bold green]✅ Tracing {self.last_trace_mode.capitalize()} selesai![/bold green]",
                border_style="green"
            ))

            summary = self.last_trace_summary or {}
            console.print(f"[dim]Total edge: {summary.get('total_edges', 0)}[/dim]")
            console.print(f"[dim]Project edges: {summary.get('project_edges', 0)} | External edges: {summary.get('external_edges', 0)}[/dim]")

            prefix = "advanced" if self.last_trace_mode == "advanced" else "standard"

            console.print("\n[bold]Pilih tindakan selanjutnya:[/bold]\n")
            console.print(f"[1] Ekspor JSON -> [yellow]{self.json_dir / f'phase2_{prefix}_graph.json'}[/yellow]")
            console.print(f"[2] Ekspor XML -> [yellow]{self.xml_dir / f'phase2_{prefix}_graph.xml'}[/yellow]")
            console.print(f"[3] Ekspor DOT -> [yellow]{self.dot_dir / f'phase2_{prefix}_graph.dot'}[/yellow]")
            console.print(f"[4] Ekspor Markdown -> [yellow]{self.md_dir / f'phase2_{prefix}_graph.md'}[/yellow]")
            console.print(f"[5] Ekspor CSV -> [yellow]{self.csv_dir / f'phase2_{prefix}_graph.csv'}[/yellow]")
            console.print("[6] Tampilkan daftar edge (relasi panggilan)")
            console.print("[7] Pilih file lain untuk tracing")
            console.print("[0] Kembali ke menu utama Phase 2")
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
                self._display_edge_list()
                Prompt.ask("[dim]Tekan Enter untuk melanjutkan[/dim]", default="")
            elif choice == "7":
                if self._select_target_script():
                    self._run_tracing()
                continue
            elif choice == "0":
                self.last_trace_result = None
                self.last_trace_mode = None
                self.last_trace_summary = None
                self.last_edge_list = None
                return
            else:  # x
                console.print("[yellow]👋 Keluar dari Phase 2.[/yellow]")
                sys.exit(0)

    # ==================== DISPLAY EDGE LIST ====================

    def _display_edge_list(self):
        """Tampilkan daftar edge dengan navigasi halaman"""
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data edge.[/yellow]")
            return

        total = len(self.last_edge_list)
        page = 0
        page_size = 15
        total_pages = (total - 1) // page_size + 1

        while True:
            console.clear()
            console.print(Panel.fit(
                f"[bold cyan]📋 Daftar Edge ({page + 1}/{total_pages})[/bold cyan]",
                border_style="cyan"
            ))

            start = page * page_size
            end = min(start + page_size, total)
            page_edges = self.last_edge_list[start:end]

            table = Table(box=box.ROUNDED)
            table.add_column("No", style="bold", width=4)
            table.add_column("Caller", style="cyan", no_wrap=True)
            table.add_column("➡️", width=4)
            table.add_column("Callee", style="green", no_wrap=True)
            table.add_column("Sumber", justify="center")
            table.add_column("Mode", justify="center")

            for i, edge in enumerate(page_edges, start=start + 1):
                caller = edge.get("caller_fqn", "")
                callee = edge.get("callee_fqn", "")
                source_type = edge.get("source_type", "project")
                # Tampilkan teks, bukan ikon
                source_text = "project" if source_type == "project" else "external"
                table.add_row(
                    str(i),
                    caller[:40] + "..." if len(caller) > 40 else caller,
                    "→",
                    callee[:40] + "..." if len(callee) > 40 else callee,
                    source_text,
                    edge.get("mode", "static")
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

    # ==================== EXPORT METHODS ====================

    def _export_json(self):
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data.[/yellow]")
            return

        prefix = "advanced" if self.last_trace_mode == "advanced" else "standard"
        output_file = self.json_dir / f"phase2_{prefix}_graph.json"

        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
            return

        data = {
            "session_info": self.last_trace_result.get("session_info", {}),
            "edges": self.last_edge_list,
            "summary": self.last_trace_summary or {},
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✅ File JSON berhasil diekspor ke {output_file}[/green]")

    def _export_xml(self):
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data.[/yellow]")
            return

        prefix = "advanced" if self.last_trace_mode == "advanced" else "standard"
        output_file = self.xml_dir / f"phase2_{prefix}_graph.xml"

        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
            return

        root = ET.Element("callgraph")
        session = ET.SubElement(root, "session_info")
        for k, v in (self.last_trace_result or {}).get("session_info", {}).items():
            e = ET.SubElement(session, k)
            e.text = str(v)

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

        console.print(f"[green]✅ File XML berhasil diekspor ke {output_file}[/green]")

    def _export_dot(self):
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data.[/yellow]")
            return

        prefix = "advanced" if self.last_trace_mode == "advanced" else "standard"
        output_file = self.dot_dir / f"phase2_{prefix}_graph.dot"

        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
            return

        dot_lines = [
            f"digraph CallGraph_{prefix} {{",
            "  rankdir=TB;",
            "  splines=ortho;",
            "  nodesep=0.8;",
            "  ranksep=1.0;",
            "  node [shape=box, style=\"rounded\", fontname=\"Arial\", fontsize=12];",
            "  edge [arrowsize=0.6, fontname=\"Arial\", fontsize=10];",
            ""
        ]

        nodes = set()
        for edge in self.last_edge_list:
            nodes.add(edge["caller_fqn"])
            nodes.add(edge["callee_fqn"])

        for node in sorted(nodes):
            is_external = any(e["callee_fqn"] == node and e["source_type"] == "external" for e in self.last_edge_list)
            color = "#eeeeee" if is_external else "#b2ebf2"
            label = node.split(".")[-1] if "." in node else node
            dot_lines.append(f'  "{node}" [label="{label}", fillcolor="{color}", style="filled"];')

        show_count = self.settings["show_call_count"]
        for edge in self.last_edge_list:
            src = edge["caller_fqn"]
            tgt = edge["callee_fqn"]
            count = edge["call_count"]
            is_external = edge["source_type"] == "external"
            color = "#ef5350" if is_external else "#42a5f5"
            dash = "5,5" if is_external else "0"
            attrs = [f'color="{color}"']
            if dash != "0":
                attrs.append('style="dashed"')
            if count > 20:
                attrs.append('penwidth=2.5')
            elif count > 5:
                attrs.append('penwidth=1.8')
            if show_count and count > 0:
                attrs.append(f'label="{count}"')
            dot_lines.append(f'  "{src}" -> "{tgt}" [' + ", ".join(attrs) + "];")

        dot_lines.append("}")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(dot_lines))

        console.print(f"[green]✅ File DOT berhasil diekspor ke {output_file}[/green]")

    def _export_md(self):
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data.[/yellow]")
            return

        prefix = "advanced" if self.last_trace_mode == "advanced" else "standard"
        output_file = self.md_dir / f"phase2_{prefix}_graph.md"

        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
            return

        lines = []
        lines.append(f"# Hasil {self.last_trace_mode.capitalize()} Tracing")
        lines.append("")
        lines.append(f"**Target Script:** `{self.target_script}`")
        lines.append(f"**Project Root:** `{self.project_root}`")
        lines.append(f"**Mode:** {self.last_trace_mode}")
        lines.append(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## Summary")
        summary = self.last_trace_summary or {}
        lines.append("| Metrik | Jumlah |")
        lines.append("|--------|--------|")
        lines.append(f"| Total Edge | {summary.get('total_edges', 0)} |")
        lines.append(f"| Project Edges | {summary.get('project_edges', 0)} |")
        lines.append(f"| External Edges | {summary.get('external_edges', 0)} |")
        lines.append(f"| File Dianalisis | {len(self.py_files)} |")
        lines.append("")
        lines.append("## Edge List")

        show_count = self.settings["show_call_count"]
        if show_count:
            lines.append("| Caller | Callee | Call Count | Source Type | Mode |")
            lines.append("|--------|--------|------------|-------------|------|")
            for edge in self.last_edge_list:
                lines.append(f"| `{edge['caller_fqn']}` | `{edge['callee_fqn']}` | {edge['call_count']} | {edge['source_type']} | {edge.get('mode', 'static')} |")
        else:
            lines.append("| Caller | Callee | Source Type | Mode |")
            lines.append("|--------|--------|-------------|------|")
            for edge in self.last_edge_list:
                lines.append(f"| `{edge['caller_fqn']}` | `{edge['callee_fqn']}` | {edge['source_type']} | {edge.get('mode', 'static')} |")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        console.print(f"[green]✅ File Markdown berhasil diekspor ke {output_file}[/green]")

    def _export_csv(self):
        if not self.last_edge_list:
            console.print("[yellow]⚠️  Tidak ada data.[/yellow]")
            return

        prefix = "advanced" if self.last_trace_mode == "advanced" else "standard"
        output_file = self.csv_dir / f"phase2_{prefix}_graph.csv"

        if output_file.exists() and not Confirm.ask(f"[yellow]⚠️  File {output_file} sudah ada. Timpa?[/yellow]", default=True):
            return

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source", "target", "call_count", "source_type", "mode"])
            for edge in self.last_edge_list:
                writer.writerow([
                    edge["caller_fqn"],
                    edge["callee_fqn"],
                    edge["call_count"],
                    edge["source_type"],
                    edge.get("mode", "static")
                ])

        console.print(f"[green]✅ File CSV berhasil diekspor ke {output_file}[/green]")


# ==================== MAIN ====================

def main():
    tracer = Phase2Tracer()
    tracer.show_menu()


if __name__ == "__main__":
    main()
