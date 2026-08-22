"""Code Project CRUD + indexing routes."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import Project, CodeFile, Symbol, Call, Import as ImportModel
from app.schemas import (
    ProjectCreate, ProjectOut, ProjectSummary, IndexRequest, IndexResult,
    SymbolOut, CallOut, FileOut, GraphData,
)
from app.services.indexer import index_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_summary(p: Project) -> ProjectSummary:
    fc = db_count(p, CodeFile) if False else None  # placeholder
    fc = p.files.__len__() if p.files else 0
    sc = p.symbols.__len__() if p.symbols else 0
    cc = p.calls.__len__() if p.calls else 0
    return ProjectSummary(
        id=p.id, name=p.name, root_path=p.root_path,
        last_indexed_at=p.last_indexed_at, created_at=p.created_at,
        file_count=fc, symbol_count=sc, call_count=cc,
    )


def db_count(p, model):
    return len(getattr(p, model.__tablename__ + 's', []) or [])


@router.get("", response_model=List[ProjectSummary])
def list_projects(db: Session = Depends(get_db)):
    items = db.query(Project).order_by(Project.created_at.desc()).all()
    return [_to_summary(p) for p in items]


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(name=payload.name, root_path=payload.root_path)
    db.add(p)
    db.commit()
    db.refresh(p)
    return ProjectOut(
        id=p.id, name=p.name, root_path=p.root_path,
        last_indexed_at=p.last_indexed_at, created_at=p.created_at,
        file_count=0, symbol_count=0, call_count=0,
        settings={},
    )


@router.get("/{pid}", response_model=ProjectOut)
def get_project(pid: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "Project not found")
    settings = {}
    if p.settings_json:
        try:
            import json
            settings = json.loads(p.settings_json)
        except Exception:
            settings = {}
    return ProjectOut(
        id=p.id, name=p.name, root_path=p.root_path,
        last_indexed_at=p.last_indexed_at, created_at=p.created_at,
        file_count=len(p.files), symbol_count=len(p.symbols), call_count=len(p.calls),
        settings=settings,
    )


@router.delete("/{pid}")
def delete_project(pid: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "Project not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/{pid}/index", response_model=IndexResult)
def trigger_index(pid: str, payload: IndexRequest, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "Project not found")
    result = index_project(
        db=db, project=p,
        include_external=payload.include_external,
        project_only_edges=payload.project_only_edges,
        dynamic_trace=payload.dynamic_trace,
        target_script=payload.target_script,
    )
    return IndexResult(
        project_id=p.id,
        duration_seconds=result["duration_seconds"],
        summary=result["summary"],
    )


@router.get("/{pid}/graph", response_model=GraphData)
def get_graph(pid: str, kind: Optional[str] = None, db: Session = Depends(get_db)):
    """Return the full graph (all symbols + all calls). Optionally filter by kind."""
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "Project not found")
    sym_q = db.query(Symbol).filter(Symbol.project_id == pid)
    if kind:
        sym_q = sym_q.filter(Symbol.kind == kind)
    symbols = sym_q.all()
    fqns = {s.fqn for s in symbols}
    call_q = db.query(Call).filter(Call.project_id == pid)
    if fqns:
        call_q = call_q.filter(Call.source_fqn.in_(fqns))
    calls = call_q.all()

    summary = {
        "total_symbols": len(symbols),
        "total_calls": len(calls),
        "entry_points": sum(1 for s in symbols if s.is_entry_point),
        "leaf_functions": sum(1 for s in symbols if s.is_leaf),
        "avg_fan_in": round(sum(s.fan_in for s in symbols) / max(1, len(symbols)), 2),
        "avg_fan_out": round(sum(s.fan_out for s in symbols) / max(1, len(symbols)), 2),
    }
    return GraphData(
        nodes=[SymbolOut.model_validate(s) for s in symbols],
        edges=[CallOut.model_validate(c) for c in calls],
        summary=summary,
    )


@router.get("/{pid}/files", response_model=List[FileOut])
def list_files(pid: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return [FileOut.model_validate(f) for f in p.files]


@router.get("/{pid}/symbols", response_model=List[SymbolOut])
def list_symbols(pid: str, kind: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Symbol).filter(Symbol.project_id == pid)
    if kind:
        q = q.filter(Symbol.kind == kind)
    if search:
        like = f"%{search}%"
        q = q.filter((Symbol.fqn.like(like)) | (Symbol.name.like(like)))
    return [SymbolOut.model_validate(s) for s in q.all()]


@router.get("/{pid}/symbols/{fqn:path}/callers", response_model=List[CallOut])
def get_callers(pid: str, fqn: str, db: Session = Depends(get_db)):
    calls = db.query(Call).filter_by(project_id=pid, target_fqn=fqn).all()
    return [CallOut.model_validate(c) for c in calls]


@router.get("/{pid}/symbols/{fqn:path}/callees", response_model=List[CallOut])
def get_callees(pid: str, fqn: str, db: Session = Depends(get_db)):
    calls = db.query(Call).filter_by(project_id=pid, source_fqn=fqn).all()
    return [CallOut.model_validate(c) for c in calls]


@router.get("/{pid}/entry-points", response_model=List[SymbolOut])
def get_entry_points(pid: str, db: Session = Depends(get_db)):
    syms = db.query(Symbol).filter_by(project_id=pid, is_entry_point=True).all()
    return [SymbolOut.model_validate(s) for s in syms]


@router.get("/{pid}/leaf-functions", response_model=List[SymbolOut])
def get_leaf_functions(pid: str, db: Session = Depends(get_db)):
    syms = db.query(Symbol).filter_by(project_id=pid, is_leaf=True).all()
    return [SymbolOut.model_validate(s) for s in syms]


@router.get("/{pid}/source")
def get_source(pid: str, path: str, line: int, context: int = 5, db: Session = Depends(get_db)):
    """Read source snippet around a line."""
    p = db.query(Project).filter(Project.id == pid).first()
    if not p:
        raise HTTPException(404, "Project not found")
    import os
    full = os.path.join(p.root_path, path)
    if not os.path.isfile(full):
        raise HTTPException(404, "File not found")
    try:
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        raise HTTPException(500, str(e))
    start = max(0, line - context - 1)
    end = min(len(lines), line + context)
    snippet = "".join(lines[start:end])
    return {
        "path": path,
        "line": line,
        "start": start + 1,
        "end": end,
        "snippet": snippet,
    }
