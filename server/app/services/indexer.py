"""Indexer — orchestrates Phase 1 → 2 → 3 → 4 and writes results to DB."""
import time
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import Project, CodeFile, Symbol, Call, Import as ImportModel
from app.services.phase1_scanner import scan_project
from app.services.phase2_tracer import trace_static, trace_dynamic
from app.services.phase3_merger import merge as merge_data
from app.services.phase4_enricher import enrich as enrich_data


def _id() -> str:
    import uuid
    return uuid.uuid4().hex[:16]


def index_project(
    db: Session,
    project: Project,
    include_external: bool = True,
    project_only_edges: bool = False,
    dynamic_trace: bool = False,
    target_script: Optional[str] = None,
) -> Dict:
    """Run full Phase 1-4 pipeline for a project. Persists results to DB."""
    t0 = time.time()

    # Clear existing data for this project (full re-index)
    db.query(Call).filter_by(project_id=project.id).delete()
    db.query(Symbol).filter_by(project_id=project.id).delete()
    db.query(CodeFile).filter_by(project_id=project.id).delete()
    db.query(ImportModel).filter_by(project_id=project.id).delete()
    db.commit()

    # === Phase 1 ===
    p1 = scan_project(project)

    # Save files
    file_id_map: Dict[str, str] = {}
    for fd in p1["files"]:
        fid = _id()
        f = CodeFile(
            id=fid, project_id=project.id, path=fd["path"],
            hash=fd["hash"], mtime=fd["mtime"], last_indexed_at=datetime.utcnow(),
        )
        db.add(f)
        file_id_map[fd["path"]] = fid
    db.flush()

    # Save symbols
    for ent in p1["entities"]:
        # Map file_path to file_id
        file_id = file_id_map.get(ent.get("file_path", ""))
        if not file_id:
            # Skip entities without a valid file (packages referencing missing __init__.py)
            if ent["kind"] == "package":
                # Use the first file in the package, or skip
                continue
            continue
        sid = _id()
        s = Symbol(
            id=sid, project_id=project.id, file_id=file_id,
            fqn=ent["fqn"], name=ent["name"], kind=ent["kind"],
            line_start=ent.get("line_start"), line_end=ent.get("line_end"),
            parent_fqn=ent.get("parent_fqn"),
        )
        db.add(s)
    db.commit()

    # === Phase 2 ===
    if dynamic_trace and target_script:
        p2_edges = trace_dynamic(project, target_script)
    else:
        p2_edges = trace_static(project)

    # === Phase 3 ===
    p3 = merge_data(
        entities=p1["entities"],
        edges=p2_edges,
        include_external=include_external,
        project_only_edges=project_only_edges,
    )

    # === Phase 4 ===
    p4 = enrich_data(p3["nodes"], p3["edges"])

    # === Persist calls + update symbol metrics ===
    # Build FQN → symbol_id map
    sym_id_map: Dict[str, str] = {
        s.fqn: s.id for s in db.query(Symbol).filter_by(project_id=project.id).all()
    }
    for e in p3["edges"]:
        # target may not exist as a project symbol
        target_id = sym_id_map.get(e["callee_fqn"])
        db.add(Call(
            id=_id(),
            project_id=project.id,
            source_fqn=e["caller_fqn"],
            target_fqn=e["callee_fqn"],
            target_name=e["callee_fqn"] if not target_id else None,
            file_path=e.get("file_path"),
            line_number=e.get("line_number"),
            call_count=e.get("call_count", 0),
            source_type=e.get("source_type", "project"),
            mode=e.get("mode", "static"),
        ))
    # Update symbol metrics
    for n in p4["nodes"]:
        s = db.query(Symbol).filter_by(project_id=project.id, fqn=n["fqn"]).first()
        if s:
            s.fan_in = n.get("fan_in", 0)
            s.fan_out = n.get("fan_out", 0)
            s.total_calls = n.get("total_calls", 0)
            s.avg_duration_seconds = n.get("avg_duration_seconds", 0.0)
            s.is_entry_point = n.get("is_entry_point", False)
            s.is_leaf = n.get("is_leaf", False)
            s.loc = n.get("loc")

    # Persist project summary
    import json
    project.last_indexed_at = datetime.utcnow()
    project.settings_json = json.dumps({
        "phase1_summary": p1["summary"],
        "phase3_summary": p3["summary"],
        "phase4_summary": p4["summary"],
    })
    db.commit()

    duration = time.time() - t0
    return {
        "duration_seconds": round(duration, 3),
        "summary": {
            "phase1": p1["summary"],
            "phase2_edges": len(p2_edges),
            "phase3": p3["summary"],
            "phase4": p4["summary"],
        },
    }
