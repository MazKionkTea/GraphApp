# Graph App

> **Unified workspace untuk Mind Map, Workflow Builder, dan Code Graph Visualizer** — satu aplikasi, tiga mode, satu database.

---

## Daftar Isi

1. [Gambaran Umum](#-gambaran-umum)
2. [Fitur](#-fitur)
3. [Arsitektur](#-arsitektur)
4. [Tech Stack](#-tech-stack)
5. [Struktur Folder](#-struktur-folder)
6. [Workflow Pengguna](#-workflow-pengguna)
7. [Skema Database](#-skema-database)
8. [API Endpoints](#-api-endpoints)
9. [Mode 1 — Mind Map](#-mode-1--mind-map)
10. [Mode 2 — Workflow](#-mode-2--workflow)
11. [Mode 3 — Code Graph](#-mode-3--code-graph)
12. [UI / Shell](#-ui--shell)
13. [Setup & Development](#-setup--development)
14. [Roadmap / Build Order](#-roadmap--build-order)
15. [Catatan & Keputusan](#-catatan--keputusan)

---

## 🎯 Gambaran Umum

**Graph App** adalah aplikasi desktop/web lokal yang menggabungkan tiga kebutuhan visualisasi graph dalam satu tempat:

| Mode | Fungsi | Untuk Siapa |
|---|---|---|
| 🧠 **Mind Map** | Brainstorming, hierarchical notes, free-form thinking | Siapa saja yang butuh susun ide |
| 🔄 **Workflow** | Bikin workflow / diagram alur proses | Tim yang desain proses kerja |
| 🐍 **Code Graph** | Visualisasi struktur & call graph project Python | Developer yang mau eksplorasi codebase |

### Visi

> Daripada punya 3 project terpisah (Python CLI untuk code analysis, React app untuk workflow, app Mind Map terpisah), **satu Graph App** yang:
> - Punya **3 mode** yang bisa di-switch dari top bar
> - Pakai **3-panel layout** yang konsisten (Navigator | Canvas | Properties)
> - Simpan semua di **satu database SQLite** (gak ada file JSON nyebar)
> - **Run lokal** dengan satu command (`./start.sh`)
> - Source data Python CLI (Phase 1–4) **di-include sebagai backend service** — gak perlu jalanin CLI terpisah

### Inspirasi Desain

- **Shell 3-panel** ala Mindomo / VS Code
- **Dark mode** sebagai default, terinspirasi VS Code palette
- **React Flow** sebagai graph engine (sama dengan existing workflow builder)
- Lihat mockup interaktif: [`docs/mockup.html`](docs/mockup.html) (akan di-generate di Phase 1)

---

## ✨ Fitur

### Common (semua mode)

- 🎨 **Dark theme default** (VS Code-inspired palette)
- 📐 **3-panel layout** responsif: Navigator | Canvas | Properties
- 🔍 **Global search** di top bar (cari node, function, mind map, dll)
- 📊 **Status bar** bawah (node count, edge count, file info)
- ↩️ **Undo/Redo** (60 steps history)
- 💾 **Autosave** ke SQLite (debounced)
- 📥 **Import**: JSON, XML, DOT, MD, CSV, OPML, FreeMind
- 📤 **Export**: PNG, SVG, JSON, MD, CSV, XML
- ⌨️ **Keyboard shortcuts** (Ctrl+Z, Ctrl+S, Ctrl+C/V, dll)
- 🎨 **Theme picker** (4 palet warna)
- 🌓 **Lock canvas** (read-only mode)

### 🧠 Mode Mind Map

- Multiple layout: **Left-Right (klasik)**, **Top-Bottom (pohon)**, **Radial**, **Free Drag**
- Hierarchical nodes dengan **parent-child** relationship
- Custom node: title, icon, color, size
- Multiple mind maps (punya list di Navigator)
- Undo/redo per mind map
- Import dari FreeMind (.mm), OPML, Markdown outline
- Export ke 5 format

### 🔄 Mode Workflow

- **Custom node** (Task): title, icon (10 emoji), color (6 preset), action dropdown (custom actions), description, collapse, disable state
- **Group node**: container, collapse/expand, ungroup, delete-with-contents
- **Custom edge**: bezier + **waypoints drag**, label editable, 6 warna, animated dash
- **Multi-workflow** (list di Navigator)
- **Snapshot** per workflow (label, timestamp, restore)
- **Status**: draft / published
- **Versioning** (track perubahan)
- **Archive** workflow
- **Autosave** debounced
- **Auto layout** (layered BFS)
- **Lock canvas** (read-only)
- Export: JSON, SVG (per workflow, per node, per group)
- Import: JSON

### 🐍 Mode Code Graph

- **Open project**: pilih folder Python → backend otomatis run Phase 1–4
- **Real file tree navigator** (dengan expand/collapse)
- **Filter per type**: package, module, class, function, method, external
- **Multiple views**:
  - **Full Graph** — semua node & edge
  - **Subgraph** — N-hop dari selected node
  - **Call Hierarchy** — tree (callers di atas, callees di bawah) ala IntelliJ
  - **Dependency View** — module-level import graph
  - **Analysis View** — color by metric (complexity, fan-in/out)
- **Properties panel** dengan tab: Info | Callers | Callees | Source | Metrics
- **Metrics** (dari Phase 4):
  - Fan-in, Fan-out
  - LOC
  - Total calls, avg duration
  - Entry points detection
  - Leaf functions detection
  - Global statistics
- **Search** global di top bar (cari function/class by name)
- **Import** file output Phase 1–4 (JSON/XML/DOT/MD/CSV)
- **Export** view (PNG/SVG/JSON/MD/CSV)
- **Multiple projects** (history di Navigator)

---

## 🏗️ Arsitektur

### High-Level

```
┌────────────────────────────────────────────────────────────────┐
│                       Graph App (Lokal)                        │
│                                                                │
│  ┌────────────────────────┐    ┌─────────────────────────┐    │
│  │  Frontend (React+Vite) │    │ Backend (FastAPI)       │    │
│  │  Port 5173             │◄──►│ Port 8765               │    │
│  │                        │    │                         │    │
│  │  ┌──────────────────┐  │    │  /api/mindmaps/*        │    │
│  │  │  3-Panel Shell   │  │    │  /api/workflows/*       │    │
│  │  │  ┌────────────┐  │  │    │  /api/projects/*        │    │
│  │  │  │ Navigator  │  │  │    │  /api/analysis/*        │    │
│  │  │  ├────────────┤  │  │    │                         │    │
│  │  │  │  Canvas    │  │  │    │  Services:              │    │
│  │  │  │  (3 mode)  │  │  │    │  ├ phase1_scanner       │    │
│  │  │  ├────────────┤  │  │    │  ├ phase2_tracer        │    │
│  │  │  │Properties │  │  │    │  ├ phase3_merger        │    │
│  │  │  └────────────┘  │  │    │  ├ phase4_enricher      │    │
│  │  └──────────────────┘  │    │  └ indexer              │    │
│  └────────────────────────┘    └──────────┬──────────────┘    │
│                                          │                     │
│                                          ▼                     │
│                              ┌──────────────────────┐         │
│                              │  SQLite (app.db)     │         │
│                              │  Single file         │         │
│                              └──────────────────────┘         │
└────────────────────────────────────────────────────────────────┘
```

### Mode Switcher

```
┌──────────────────────────────────────────────────────────────────┐
│  [🧠 Mind Map]  [🔄 Workflow]  [🐍 Code Graph]    🔍 search  ⚙️ │
├───────────────┬──────────────────────────────┬──────────────────┤
│               │                              │                  │
│  Navigator    │           Canvas             │   Properties     │
│  (per mode)   │        (per mode)            │   (per mode)     │
│               │                              │                  │
├───────────────┴──────────────────────────────┴──────────────────┤
│  Status: 14 nodes · 23 edges · project: myapp                   │
└──────────────────────────────────────────────────────────────────┘
```

Klik salah satu tab mode → Navigator, Canvas, Properties ganti konten sesuai mode yang aktif.

### Data Flow — Code Graph

```
User: "Open project" → pilih folder Python
            │
            ▼
   POST /api/projects/{id}/analyze
            │
            ▼
   ┌────────────────────────────────────┐
   │  Backend pipeline (async)         │
   │                                    │
   │  Phase 1: scan struktur project    │
   │      │                             │
   │      ▼                             │
   │  Phase 2: tracing call (static)    │
   │      │                             │
   │      ▼                             │
   │  Phase 3: merge + filter           │
   │      │                             │
   │      ▼                             │
   │  Phase 4: enrichment + metrics     │
   │      │                             │
   │      ▼                             │
   │  Simpan ke SQLite                  │
   └────────────────────────────────────┘
            │
            ▼
   GET /api/projects/{id}/graph
            │
            ▼
   Frontend: render React Flow + 3-panel UI
```

---

## 🧱 Tech Stack

| Layer | Teknologi | Versi | Alasan |
|---|---|---|---|
| **Frontend Framework** | React | 18+ | Standar industri, ekosistem besar |
| **Build Tool** | Vite | 5+ | Cepat, HMR instant |
| **Language** | TypeScript | 5+ | Type-safe, refactor-friendly |
| **Graph Engine** | `@xyflow/react` (React Flow) | 12+ | Library #1 untuk node-based UI, sama dengan existing workflow builder |
| **State Management** | Zustand | 4+ | Ringan, ada middleware untuk undo/redo |
| **Styling** | Tailwind CSS | 3+ | Utility-first, cepat |
| **UI Components** | shadcn/ui | latest | Copy-paste, customizable, dark mode ready |
| **Icons** | lucide-react | latest | Tree-shakable, konsisten |
| **Date utils** | date-fns | 3+ | Ringan, modular |
| **Backend Framework** | FastAPI | 0.110+ | Modern, async, type hints, auto docs |
| **ORM** | SQLAlchemy | 2+ | Standard Python, type-safe |
| **Migrations** | Alembic | latest | Standard SQLAlchemy migration tool |
| **DB** | SQLite | 3+ | Single file, no infra, perfect untuk lokal |
| **Code Parsing** | `ast` (stdlib) | 3.x | Built-in, no install |
| **Code Metrics** | `radon` | latest | Cyclomatic complexity, LOC |
| **Server** | Uvicorn | latest | ASGI server untuk FastAPI |
| **CORS** | fastapi.middleware.cors | built-in | Allow frontend access |

---

## 📂 Struktur Folder

```
graph-app/
├── client/                          # React + Vite + TypeScript
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── shell/                   # 3-panel layout + mode switcher (shared)
│   │   │   ├── Layout.tsx           # Main grid: topbar | 3-panel | statusbar
│   │   │   ├── ModeSwitcher.tsx     # Tab Mind Map / Workflow / Code Graph
│   │   │   ├── TopBar.tsx           # Brand + search + actions
│   │   │   ├── Navigator.tsx        # Left panel (mode-aware)
│   │   │   ├── Canvas.tsx           # Center panel (mode-aware)
│   │   │   ├── Properties.tsx       # Right panel (mode-aware)
│   │   │   ├── SearchBar.tsx        # Global search input
│   │   │   └── StatusBar.tsx        # Bottom info bar
│   │   ├── modes/
│   │   │   ├── mindmap/             # Mode Mind Map
│   │   │   │   ├── MindMapCanvas.tsx
│   │   │   │   ├── MindMapNode.tsx  # Custom node
│   │   │   │   ├── layouts/
│   │   │   │   │   ├── leftRight.ts # Algoritma LR
│   │   │   │   │   ├── topBottom.ts # Algoritma TB
│   │   │   │   │   ├── radial.ts    # Algoritma radial
│   │   │   │   │   └── free.ts      # Free drag (no-op)
│   │   │   │   ├── MindMapNavigator.tsx
│   │   │   │   ├── MindMapProperties.tsx
│   │   │   │   ├── Toolbar.tsx
│   │   │   │   └── store.ts         # Zustand store khusus mode
│   │   │   ├── workflow/            # Mode Workflow (port dari existing)
│   │   │   │   ├── WorkflowCanvas.tsx
│   │   │   │   ├── nodes/
│   │   │   │   │   ├── TaskNode.tsx       # Port dari CustomNode
│   │   │   │   │   ├── GroupNode.tsx      # Port dari GroupNode
│   │   │   │   │   └── ActionDropdown.tsx # Port
│   │   │   │   ├── edges/
│   │   │   │   │   └── CustomEdge.tsx     # Port dengan waypoints
│   │   │   │   ├── panels/
│   │   │   │   │   ├── Toolbar.tsx        # Port dengan penyesuaian
│   │   │   │   │   ├── WorkflowPanel.tsx  # Modal list workflow
│   │   │   │   │   └── SnapshotPanel.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useUndoRedo.ts
│   │   │   │   ├── WorkflowNavigator.tsx
│   │   │   │   ├── WorkflowProperties.tsx
│   │   │   │   └── store.ts
│   │   │   └── codemap/             # Mode Code Graph
│   │   │       ├── CodeMapCanvas.tsx
│   │   │       ├── CodeNode.tsx     # Custom node per symbol type
│   │   │       ├── views/
│   │   │       │   ├── FullGraph.tsx
│   │   │       │   ├── Subgraph.tsx
│   │   │       │   ├── CallHierarchy.tsx
│   │   │       │   ├── DependencyView.tsx
│   │   │       │   └── AnalysisView.tsx
│   │   │       ├── CodeMapNavigator.tsx   # File tree
│   │   │       ├── CodeMapProperties.tsx  # Tab Info/Callers/Callees/Source/Metrics
│   │   │       ├── Toolbar.tsx            # Open project, filter, view switcher
│   │   │       └── store.ts
│   │   ├── importers/               # Format-agnostic file loaders
│   │   │   ├── index.ts             # Dispatcher by file type
│   │   │   ├── json.ts              # Phase 1/2/3/4 JSON, FreeMind
│   │   │   ├── xml.ts               # Phase 1/2/3/4 XML, OPML
│   │   │   ├── dot.ts               # Phase 2/3/4 DOT
│   │   │   ├── md.ts                # Phase 1/2/3/4 Markdown
│   │   │   ├── csv.ts               # Phase 2/3/4 CSV
│   │   │   └── normalize.ts         # Convert ke GraphData unified model
│   │   ├── exporters/               # Format writers
│   │   │   ├── png.ts               # html-to-image
│   │   │   ├── svg.ts               # Vector export
│   │   │   ├── json.ts
│   │   │   ├── md.ts
│   │   │   ├── csv.ts
│   │   │   └── xml.ts
│   │   ├── api/                     # Backend client
│   │   │   ├── client.ts            # fetch wrapper
│   │   │   ├── mindmaps.ts          # Mind map endpoints
│   │   │   ├── workflows.ts         # Workflow endpoints
│   │   │   ├── projects.ts          # Code project endpoints
│   │   │   └── analysis.ts          # Phase 1-4 triggers
│   │   ├── store/                   # Global stores
│   │   │   ├── useAppStore.ts       # Mode aktif, settings
│   │   │   ├── useThemeStore.ts     # Dark/light
│   │   │   └── useHistoryStore.ts   # Undo/redo global
│   │   ├── components/              # Shared UI
│   │   │   └── ui/                  # shadcn components
│   │   ├── lib/                     # Utilities
│   │   │   ├── id.ts                # nanoid wrapper
│   │   │   ├── debounce.ts
│   │   │   └── format.ts
│   │   ├── types/                   # TypeScript types
│   │   │   ├── mindmap.ts
│   │   │   ├── workflow.ts
│   │   │   ├── codemap.ts
│   │   │   └── common.ts
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── App.tsx                  # Root: <Layout />
│   │   └── main.tsx                 # Entry
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── postcss.config.js
│   ├── components.json              # shadcn config
│   └── package.json
│
├── server/                          # Python FastAPI
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, CORS, mount routes
│   │   ├── config.py                # Settings (path DB, port, dll)
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py            # GET /api/health
│   │   │   ├── mindmaps.py          # CRUD mindmaps
│   │   │   ├── workflows.py         # CRUD workflows, snapshots
│   │   │   ├── projects.py          # CRUD code projects
│   │   │   └── analysis.py          # Trigger Phase 1-4
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── phase1_scanner.py    # Port dari existing Phase1Scanner
│   │   │   ├── phase2_tracer.py     # Port: standard (static) + advanced (dynamic)
│   │   │   ├── phase3_merger.py     # Port dari existing Phase3Merger
│   │   │   ├── phase4_enricher.py   # Port dari existing Phase4Enricher
│   │   │   ├── indexer.py           # Orchestrator: jalankan 1-4
│   │   │   ├── exporter.py          # 5 format writers
│   │   │   └── importer.py          # 5 format readers
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # SQLAlchemy models (semua tabel)
│   │   │   ├── session.py           # DB engine, session factory
│   │   │   ├── base.py              # Declarative base
│   │   │   └── migrations/          # Alembic
│   │   │       ├── versions/
│   │   │       └── env.py
│   │   ├── schemas/                 # Pydantic schemas
│   │   │   ├── mindmap.py
│   │   │   ├── workflow.py
│   │   │   ├── codemap.py
│   │   │   └── common.py
│   │   └── utils/
│   │       ├── ast_helpers.py       # Custom AST utilities
│   │       ├── graph_utils.py       # Graph algorithms
│   │       └── file_utils.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── pyproject.toml
│
├── data/                            # Runtime data (gitignored)
│   ├── app.db                       # SQLite database
│   ├── uploads/                     # Uploaded files
│   └── logs/
│       ├── backend.log
│       └── frontend.log
│
├── docs/                            # Documentation
│   ├── mockup.html                  # Interactive UI mockup
│   ├── architecture.md              # Detailed architecture
│   ├── api.md                       # API documentation
│   └── screenshots/
│
├── scripts/                         # Utility scripts
│   ├── init_db.py                   # Initialize DB
│   ├── reset_db.py                  # Reset DB
│   └── seed_data.py                 # Seed sample data
│
├── tests/                           # Test suite
│   ├── client/
│   ├── server/
│   └── e2e/
│
├── .gitignore
├── .env.example                     # Environment variables template
├── start.sh                         # Linux/macOS launcher
├── start.bat                        # Windows launcher
├── stop.sh                          # Stop both processes
└── README.md                        # ← you are here
```

### Penjelasan Struktur

- **`client/`** — Semua kode frontend React. Setiap mode punya folder sendiri di `modes/`, dengan `Canvas`, `Navigator`, `Properties` masing-masing. Shell di `shell/` adalah shared.
- **`server/`** — Backend FastAPI. Logic Phase 1-4 di `services/`, port dari existing Python CLI. DB models di `db/`.
- **`data/`** — Runtime files, gak di-commit ke git.
- **`docs/`** — Dokumentasi, mockup, screenshot.
- **`scripts/`** — Utility scripts (init DB, reset, seed).
- **`tests/`** — Test suite (akan ditambah di akhir).

---

## 🔄 Workflow Pengguna

### Skenario 1: Bikin Mind Map

```
1. Buka Graph App
2. Klik tab "Mind Map" (di top bar)
3. Klik "+ New Mind Map" (di Navigator)
4. Tulis judul mind map
5. Double-click canvas → bikin root node
6. Double-click node → bikin child
7. Drag node → atur posisi
8. Klik node → edit di Properties panel
9. Pilih layout (LR / TB / Radial / Free)
10. Klik "Save" (autosave juga jalan)
11. Export ke PNG / JSON / MD / etc
```

### Skenario 2: Bikin Workflow

```
1. Klik tab "Workflow"
2. Klik "+ New Workflow" 
3. Tekan "A" atau klik "+ Node" → bikin task
4. Drag dari handle satu node ke node lain → bikin connection
5. Right-click pada edge → tambah waypoint
6. Klik node → edit title, icon, color, action di Properties
7. Select multiple nodes → Ctrl+G → bikin group
8. Save (autosave)
9. Snapshot (📸) untuk save state tertentu
10. Export JSON / SVG
```

### Skenario 3: Visualisasi Code Graph

```
1. Klik tab "Code Graph"
2. Klik "Open Project" → pilih folder Python
3. Backend otomatis jalanin Phase 1-4 (background)
4. Setelah selesai, file tree muncul di Navigator
5. Pilih file/class/function → graph render di Canvas
6. Switch view: Full / Subgraph / Call Hierarchy / Dependency
7. Klik node → Properties panel show info + callers + callees + metrics
8. Filter by type (package/module/class/function/method)
9. Search function name di top bar
10. Export view ke PNG / SVG / JSON
```

### Skenario 4: Import File Existing

```
1. Klik "Import" di top bar
2. Pilih file (.json, .xml, .dot, .md, .csv)
3. Parser auto-detect format
4. Data di-normalize ke unified model
5. Switch ke mode yang sesuai (atau tanya user)
6. Render di Canvas
```

---

## 🗃️ Skema Database

SQLite schema, semua mode dalam satu database.

### Mind Map Tables

```sql
mindmaps (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  theme TEXT DEFAULT 'default',
  layout TEXT DEFAULT 'free',  -- 'lr' | 'tb' | 'radial' | 'free'
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

mindmap_nodes (
  id TEXT PRIMARY KEY,
  mindmap_id TEXT REFERENCES mindmaps(id) ON DELETE CASCADE,
  label TEXT,
  icon TEXT,
  color TEXT,
  pos_x REAL,
  pos_y REAL,
  parent_id TEXT REFERENCES mindmap_nodes(id),
  created_at TIMESTAMP
)

mindmap_edges (
  id TEXT PRIMARY KEY,
  mindmap_id TEXT REFERENCES mindmaps(id) ON DELETE CASCADE,
  source_id TEXT REFERENCES mindmap_nodes(id) ON DELETE CASCADE,
  target_id TEXT REFERENCES mindmap_nodes(id) ON DELETE CASCADE,
  label TEXT
)
```

### Workflow Tables

```sql
workflows (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'draft',  -- 'draft' | 'published'
  version INTEGER DEFAULT 1,
  archived BOOLEAN DEFAULT 0,
  viewport_json TEXT,  -- JSON: { x, y, zoom }
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

workflow_nodes (
  id TEXT PRIMARY KEY,
  workflow_id TEXT REFERENCES workflows(id) ON DELETE CASCADE,
  type TEXT,  -- 'task' | 'group'
  position_x REAL,
  position_y REAL,
  width REAL,
  height REAL,
  parent_id TEXT,
  data_json TEXT,  -- JSON: { title, icon, color, action, description, ... }
  hidden BOOLEAN DEFAULT 0
)

workflow_edges (
  id TEXT PRIMARY KEY,
  workflow_id TEXT REFERENCES workflows(id) ON DELETE CASCADE,
  source_id TEXT REFERENCES workflow_nodes(id) ON DELETE CASCADE,
  target_id TEXT REFERENCES workflow_nodes(id) ON DELETE CASCADE,
  data_json TEXT  -- JSON: { label, color, waypoints, animated }
)

workflow_snapshots (
  id TEXT PRIMARY KEY,
  workflow_id TEXT REFERENCES workflows(id) ON DELETE CASCADE,
  label TEXT,
  nodes_json TEXT,
  edges_json TEXT,
  created_at TIMESTAMP
)
```

### Code Project Tables

```sql
projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  root_path TEXT NOT NULL,
  last_indexed_at TIMESTAMP,
  created_at TIMESTAMP,
  settings_json TEXT
)

files (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  path TEXT NOT NULL,
  hash TEXT,
  mtime REAL,
  last_indexed_at TIMESTAMP
)

symbols (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  file_id TEXT REFERENCES files(id) ON DELETE CASCADE,
  fqn TEXT NOT NULL,  -- Fully Qualified Name
  name TEXT NOT NULL,
  kind TEXT NOT NULL,  -- 'package' | 'module' | 'class' | 'function' | 'method'
  line_start INTEGER,
  line_end INTEGER,
  parent_id TEXT REFERENCES symbols(id),
  complexity INTEGER,
  loc INTEGER,
  UNIQUE(project_id, fqn)
)

calls (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  source_id TEXT REFERENCES symbols(id) ON DELETE CASCADE,
  target_id TEXT REFERENCES symbols(id),  -- nullable untuk external
  target_name TEXT,  -- kalau target_id null
  file_id TEXT REFERENCES files(id),
  line_number INTEGER,
  call_count INTEGER DEFAULT 0,
  total_time_seconds REAL DEFAULT 0,
  source_type TEXT DEFAULT 'project'  -- 'project' | 'external'
)

imports (
  id TEXT PRIMARY KEY,
  project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
  source_file_id TEXT REFERENCES files(id) ON DELETE CASCADE,
  module_name TEXT,
  imported_names_json TEXT
)
```

### Settings Table

```sql
settings (
  key TEXT PRIMARY KEY,
  value TEXT,  -- JSON
  updated_at TIMESTAMP
)
```

---

## 🌐 API Endpoints

Base URL: `http://localhost:8765/api`

### Health
- `GET /api/health` → `{"ok": true, "version": "0.1.0"}`

### Mind Maps
- `GET    /api/mindmaps` — List all
- `POST   /api/mindmaps` — Create new
- `GET    /api/mindmaps/{id}` — Get detail (with nodes & edges)
- `PUT    /api/mindmaps/{id}` — Update
- `DELETE /api/mindmaps/{id}` — Delete
- `POST   /api/mindmaps/{id}/autosave` — Autosave nodes/edges

### Workflows
- `GET    /api/workflows` — List all
- `POST   /api/workflows` — Create new
- `GET    /api/workflows/{id}` — Get detail
- `PUT    /api/workflows/{id}` — Update
- `DELETE /api/workflows/{id}` — Delete
- `POST   /api/workflows/{id}/archive` — Toggle archive
- `POST   /api/workflows/{id}/clone` — Clone
- `GET    /api/workflows/{id}/snapshots` — List snapshots
- `POST   /api/workflows/{id}/snapshots` — Create snapshot
- `POST   /api/workflows/{id}/snapshots/{snap_id}/restore` — Restore
- `DELETE /api/workflows/{id}/snapshots/{snap_id}` — Delete snapshot

### Action Options (for workflow)
- `GET    /api/actions` — List custom actions
- `POST   /api/actions` — Add
- `PUT    /api/actions/{name}` — Rename
- `DELETE /api/actions/{name}` — Delete

### Code Projects
- `GET    /api/projects` — List all indexed projects
- `POST   /api/projects` — Register new project
- `GET    /api/projects/{id}` — Get detail
- `DELETE /api/projects/{id}` — Delete + all data
- `POST   /api/projects/{id}/index` — Trigger re-indexing (Phase 1-4)

### Analysis (per project)
- `GET    /api/projects/{id}/graph` — Get full graph (nodes + edges)
- `GET    /api/projects/{id}/files` — List files
- `GET    /api/projects/{id}/symbols` — List symbols (with filter)
- `GET    /api/projects/{id}/symbols/{fqn}/callers` — Get callers
- `GET    /api/projects/{id}/symbols/{fqn}/callees` — Get callees
- `GET    /api/projects/{id}/metrics` — Global metrics (Phase 4)
- `GET    /api/projects/{id}/entry-points` — Entry points
- `GET    /api/projects/{id}/leaf-functions` — Leaf functions

### Import/Export
- `POST   /api/import` — Upload file (multipart), auto-detect format, normalize
- `POST   /api/export` — Export current view to format

---

## 🧠 Mode 1 — Mind Map

### Fitur Detail

- **Multiple layouts**:
  - **Left-Right (LR)**: Mind map klasik, root di tengah, cabang ke kiri & kanan
  - **Top-Bottom (TB)**: Pohon vertikal, root di atas
  - **Radial**: Root di tengah, branches melingkar
  - **Free**: Drag manual tanpa auto-layout
- **Node operations**:
  - Create (double-click canvas)
  - Edit label, icon, color
  - Delete (select + Delete key)
  - Reparent (drag onto another node)
  - Expand/collapse subtree
- **Canvas operations**:
  - Zoom, pan
  - Fit-to-view
  - Mini-map
  - Grid background
- **Persistence**:
  - Auto-save (debounced 800ms)
  - Manual save
  - Multiple mind maps (list in Navigator)
  - Recent mind maps
- **Theme**:
  - 4 palet warna preset
  - Custom accent color
- **Import/Export**:
  - Import: JSON (native), FreeMind XML, OPML, Markdown outline
  - Export: JSON, XML (FreeMind), MD, CSV, SVG, PNG

---

## 🔄 Mode 2 — Workflow

### Fitur Detail

#### Task Node
- **Title** (editable, double-click)
- **Icon** (10 emoji: 📝 ⚙️ 📧 🔔 🗂️ 🔗 ⏱️ 🧩 📊 🧪)
- **Color** (6 preset: blue, green, amber, red, purple, slate)
- **Action** (custom dropdown, user-managed di settings)
- **Description** (collapsible textarea)
- **State**:
  - Collapsed (hide body)
  - Disabled (greyed out)
- **Toolbar actions** (saat selected):
  - Color picker
  - Icon picker
  - Collapse/expand
  - Disable/enable
  - Duplicate
  - Export as SVG
  - Delete
- **Connection handles**: 8 (top, bottom, left, right × 2 each)
- **Resizer** (saat selected, kalau gak collapsed)

#### Group Node
- **Title** (editable)
- **Color** (with transparent background)
- **Collapse/expand** (hide/show children)
- **Ungroup** (release children, keep positions)
- **Delete with contents**
- **Resizer** (saat expanded)
- **Count badge** (saat collapsed)

#### Custom Edge
- **Bezier path** (default) atau **polyline** (kalau ada waypoint)
- **Waypoints**:
  - Right-click pada edge → tambah waypoint
  - Drag waypoint → pindah posisi
  - Right-click pada waypoint → hapus
- **Label** (editable, double-click)
- **Color** (6 preset)
- **Animation** (dashed, scroll)
- **Menu** (right-click on label chip):
  - Edit label
  - Toggle animation
  - Change color
  - Reset route (hapus waypoints)
  - Delete connection

#### Workflow Manager
- **Multi-workflow** (list di Navigator)
- Per workflow:
  - Name (editable)
  - Status: draft / published (click badge to toggle)
  - Version (auto-increment)
  - Archived (toggle)
  - Created/updated timestamps
- Operations:
  - New, Open, Clone, Archive, Delete
  - Snapshot (label + restore + delete)
  - Import JSON, Export JSON
  - Export SVG (full canvas, per-node, per-group)

#### Persistence
- Auto-save (debounced 800ms)
- Manual save (Ctrl+S)
- Snapshots (named, restorable)

### Catatan Porting dari Existing

Yang di-port dari existing 10 file:
- `CustomNode` → `TaskNode.tsx` (mostly same, adjust import paths)
- `GroupNode` → `GroupNode.tsx` (same)
- `CustomEdge` → `CustomEdge.tsx` (same)
- `ActionDropdown` → `ActionDropdown.tsx` (same)
- `Toolbar` → `Toolbar.tsx` (mostly same, add API integration)
- `WorkflowPanel` → `WorkflowPanel.tsx` + `SnapshotPanel.tsx`
- `useUndoRedo` → `hooks/useUndoRedo.ts` (mostly same)
- `exportImage` → `exporters/svg.ts` (refactored)
- `id.js` → `lib/id.ts`
- `storage.js` → **diganti total** dengan `api/workflows.ts` (FastAPI client)

Yang **berubah**:
- Storage: `localStorage` → SQLite via FastAPI
- ID generation: `nanoid` (sama)
- State management: `useState` + `useNodesState` → Zustand store
- Bahasa UI: Indonesia (existing) → **tetap Indonesia** (konsisten)

---

## 🐍 Mode 3 — Code Graph

### Pipeline Backend (Phase 1-4)

**Phase 1 — Static Code Inspection** (`phase1_scanner.py`)
- Scan folder `.py`
- Extract entities: packages, modules, classes, functions, methods
- Pakai `ast` module
- Output: simpan ke tabel `files`, `symbols`

**Phase 2 — Function Tracing** (`phase2_tracer.py`)
- **Standard (static)**: Analisis AST, kumpulkan call edges
- **Advanced (dynamic)**: `sys.settrace`, run target script, capture runtime calls
- Output: simpan ke tabel `calls` (dengan `mode` field)

**Phase 3 — Merge & Filter** (`phase3_merger.py`)
- Combine Phase 1 + Phase 2
- Apply filter: `include_external_nodes`, `filter_project_edges_only`
- Output: enriched nodes+edges view (computed on-the-fly atau materialized)

**Phase 4 — Enrichment** (`phase4_enricher.py`)
- Hitung per symbol:
  - `fan_in` (jumlah caller unik)
  - `fan_out` (jumlah callee unik)
  - `loc` (line_end - line_start + 1)
  - `total_calls` (sum dari edge call_count)
  - `avg_duration_seconds`
  - `is_entry_point` (fan_in == 0, type function/method)
  - `is_leaf` (fan_out == 0, type function/method)
- Hitung global stats: avg/max fan-in/out, max total_calls, list entry_points, leaf_functions
- Simpan ke `symbols.metrics_json` dan agregat di `projects.settings_json`

### Frontend Views

#### Full Graph
- Semua nodes & edges dalam React Flow
- Color by type (package=green, module=blue, class=amber, function=cyan, method=purple, external=gray)
- Layout: dagre TB/LR (auto)
- Filter: by type, by file
- Edge: arrow, optional label (call_count)

#### Subgraph
- N-hop dari selected node (default 1)
- "Expand" button untuk tambah hop
- Highlight selected + neighbors
- Dim yang lain

#### Call Hierarchy
- Tree-view dari selected function
- Atas: callers (recursive)
- Bawah: callees (recursive)
- Style: collapsible tree (IntelliJ-like)

#### Dependency View
- Module-level only
- Edges = `import` statements
- Detect circular imports → highlight merah
- Click module → show imported + imported_by

#### Analysis View
- Color nodes by metric:
  - Red: high fan_in (>10) atau high complexity
  - Amber: medium
  - Green: low
- Toggle: highlight entry points, highlight leaf functions, highlight dead code
- Top-N list: most complex, most called, etc

### Properties Panel — Tabs

**Info**
- FQN, type, parent_fqn
- File path, line_start, line_end
- Module info

**Callers**
- List of all callers (from `calls` table)
- Click → navigate to that symbol

**Callees**
- List of all callees
- Click → navigate

**Source**
- Read file from `root_path`
- Show snippet (line_start ± 5 lines)
- Syntax highlight (Python)
- "Open in editor" button (open file with default app, OS-level)

**Metrics**
- Cards: fan_in, fan_out, complexity, loc, total_calls, avg_duration
- Visual indicators (good/warn/bad)
- "is_entry_point" / "is_leaf" badges

---

## 🎨 UI / Shell

### 3-Panel Layout (Shared)

```
┌────────────────────────────────────────────────────────────────┐
│  TopBar: Brand | Mode Switcher | Search | Actions              │  44px
├──────────────┬─────────────────────────────────┬───────────────┤
│              │                                 │               │
│  Navigator   │         Canvas                  │  Properties   │  flex
│  (280px)     │         (1fr)                   │  (320px)      │
│              │                                 │               │
│              │                                 │               │
│              │                                 │               │
├──────────────┴─────────────────────────────────┴───────────────┤
│  StatusBar: nodes, edges, project, view                        │  26px
└────────────────────────────────────────────────────────────────┘
```

### Mode Switcher

Tiga tab di top bar:
- 🧠 **Mind Map** — dengan badge jumlah mind map
- 🔄 **Workflow** — dengan badge jumlah workflow
- 🐍 **Code Graph** — dengan badge jumlah project

Klik → switch mode. State: `useAppStore.mode`

### Theme

- **Dark default** (VS Code palette: `#0d1117` bg, `#58a6ff` accent)
- Toggle ke light (optional)
- Persistent di localStorage + `settings` table

### Keyboard Shortcuts (Global)

- `Ctrl/Cmd + K` — Focus search
- `Ctrl/Cmd + 1/2/3` — Switch mode (1=Mind Map, 2=Workflow, 3=Code Graph)
- `Ctrl/Cmd + S` — Save
- `Ctrl/Cmd + Z` — Undo
- `Ctrl/Cmd + Shift + Z` atau `Ctrl/Cmd + Y` — Redo
- `Ctrl/Cmd + C/V` — Copy/Paste
- `Ctrl/Cmd + A` — Select all
- `Ctrl/Cmd + D` — Duplicate
- `F` — Fit view
- `L` — Lock canvas
- `Delete/Backspace` — Delete selected

---

## 🛠️ Setup & Development

### Prerequisites

- **Node.js** 20+ (`node --version`)
- **Python** 3.11+ (`python --version`)
- **npm** atau **pnpm** (`npm --version`)
- **Git**
- **Rust toolchain** + C/C++ compiler (hanya kalau `pydantic-core` gagal build dari source — biasanya sudah ada pre-built wheel)

### Quick Start

```bash
./start.sh          # start backend + frontend
./status.sh         # cek status
./stop.sh           # stop
```

URL: **http://127.0.0.1:5173** (frontend) · **http://127.0.0.1:8765** (backend)

### Manual Setup (kalau `start.sh` gagal)

```bash
# Backend
cd server
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
cd .. && python scripts/init_db.py

# Frontend
cd client
npm install
```

### Jalankan Manual (debugging)

```bash
# Terminal 1 — backend
cd server && source venv/bin/activate
uvicorn app.main:app --reload --port 8765

# Terminal 2 — frontend
cd client
npm run dev
```

### Reset Database

```bash
rm -f data/app.db
python scripts/init_db.py
```

### 🩹 Troubleshooting

#### ❌ `Failed to build installable wheels for pydantic-core`

`pydantic-core` butuh Rust untuk compile dari source. Biasanya pre-built wheel udah ada, tapi kalau gagal:

**Fix 1 — Install Rust toolchain:**
```bash
./install_deps.sh       # auto-detect distro (Arch/Debian/Fedora/openSUSE)
# atau manual:
# Arch:    sudo pacman -S base-devel rust
# Ubuntu:  sudo apt install build-essential rustc cargo
# Fedora:  sudo dnf install gcc gcc-c++ rust cargo
```

**Fix 2 — Force wheel (no compile):**
```bash
./venv/bin/pip install --only-binary=:all: -r requirements.txt
```

**Fix 3 — Upgrade pip dulu:**
```bash
./venv/bin/pip install --upgrade pip wheel
```

#### ❌ App berhenti sendiri setelah tutup terminal

`start.sh` pakai `setsid` untuk detach beneran. Kalau masih mati:

1. Cek pakai `status.sh` — masih running atau engga
2. Cek log: `tail -f data/logs/backend.log`
3. Pastikan `data/pids/*.pid` ada
4. Jangan close terminal dengan Ctrl+C — pakai `./stop.sh` atau biarkan terminal terbuka

#### ❌ `Port already in use`

```bash
# Cari proses yang pakai port
sudo ss -tlnp | grep 8765      # backend
sudo ss -tlnp | grep 5173      # frontend
# Kill manual
sudo kill <PID>
# Atau langsung
sudo kill $(sudo lsof -t -i:8765)    # backend
sudo kill $(sudo lsof -t -i:5173)    # frontend
```

#### ❌ `node-gyp` atau build error di npm install

Biasanya karena versi Node terlalu lama atau build tool missing.

```bash
node --version    # harus 20+
# Arch:    sudo pacman -S nodejs npm gcc
# Ubuntu:  sudo apt install nodejs npm build-essential
```

#### ❌ `data/app.db` corrupt / locked

```bash
./stop.sh
rm -f data/app.db data/pids/*.pid
python scripts/init_db.py
./start.sh
```

### Akses

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8765
- **API Docs (Swagger)**: http://localhost:8765/docs
- **API Docs (ReDoc)**: http://localhost:8765/redoc

### Build (Production)

```bash
# Frontend
cd client
npm run build
# Output di client/dist/

# Backend (gak perlu build, langsung run)
cd ../server
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

---

## 🗺️ Roadmap / Build Order

| Phase | Scope | Output | Estimasi |
|---|---|---|---|
| **Phase 1: Foundation** | Project skeleton, backend setup, frontend shell, 3-panel, mode switcher, dark theme, DB schema, start script | App jalan dengan 3 mode placeholder | 3–4 hari |
| **Phase 2: Mind Map** | Mind map mode lengkap (CRUD, layout 4 jenis, themes, import/export 5 format) | Mind map mode usable | 2–3 hari |
| **Phase 3: Workflow** | Port existing workflow builder ke mode/workflow, integrate API | Workflow mode usable, semua fitur existing keep | 3–4 hari |
| **Phase 4: Code Graph** | Port Phase 1-4 Python CLI ke backend services, build 3-panel Code Graph UI dengan 5 views | Code graph mode usable, full pipeline | 4–5 hari |
| **Polish** | Bug fixes, edge cases, performance, docs | Production-ready (lokal) | 2–3 hari |

**Total: ~14–19 hari kalender**

---

## 📝 Catatan & Keputusan

### Keputusan yang udah dibuat:

1. **Backend = Python (FastAPI)** — biar bisa reuse logic Phase 1-4 existing
2. **DB = SQLite** — single file, no infra, perfect untuk lokal/tim kecil
3. **Frontend = React + Vite + TS** — standar modern, ekosistem besar
4. **Graph engine = React Flow (`@xyflow/react`)** — sama dengan existing workflow, biar porting mulus
5. **3 modes (Mind Map, Workflow, Code Graph)** — bukan 1 tool, 3 tool dalam 1 shell
6. **3-panel layout ala Mindomo** — Navigator | Canvas | Properties
7. **Dark mode default** — VS Code-inspired
8. **Storage terpusat** — semua di SQLite, bukan localStorage + file JSON
9. **Build order C** — Foundation → Mind Map → Workflow → Code Graph
10. **Deployment lokal** — single command (`./start.sh`), bukan production-scale

### Hal yang masih open (bisa di-discuss):

- **Auth** — gak ada, single user (atau multi-user tanpa login, share by file path?). Local-only assumption
- **Multi-window** — belum, single tab
- **Mobile** — gak di-target, desktop only
- **Code editor integration** — open file di editor external (VS Code) — perlu konfirmasi
- **Git integration** — auto-commit versioned workflow? — belum
- **Collaboration** — gak real-time, single user

### Sumber Referensi

- Existing Workflow Builder (10 file React) → akan di-port ke `client/src/modes/workflow/`
- Existing Python CLI (Phase 1-4) → akan di-port ke `server/app/services/`
- Mockup interaktif: `docs/mockup.html`

---

## 📜 License

TBD (personal/local project)

---

**Status**: 📋 Planning complete, awaiting Phase 1 kick-off.
