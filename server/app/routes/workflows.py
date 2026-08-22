"""Workflow CRUD + snapshot + action options routes."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import Workflow, WorkflowNode, WorkflowEdge, WorkflowSnapshot, ActionOption
from app.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowOut, WorkflowSummary,
    WorkflowNodeCreate, WorkflowNodeOut, WorkflowEdgeCreate, WorkflowEdgeOut,
    SnapshotCreate, SnapshotOut, ActionOptionOut,
)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _to_out(w: Workflow) -> WorkflowOut:
    viewport = None
    if w.viewport_json:
        try:
            viewport = json.loads(w.viewport_json)
        except Exception:
            viewport = None
    return WorkflowOut(
        id=w.id, name=w.name, status=w.status, version=w.version, archived=w.archived,
        viewport=viewport, created_at=w.created_at, updated_at=w.updated_at,
        nodes=[WorkflowNodeOut(
            id=n.id, type=n.type, position_x=n.position_x, position_y=n.position_y,
            width=n.width, height=n.height, parent_id=n.parent_id, hidden=n.hidden,
            data=json.loads(n.data_json) if n.data_json else {},
        ) for n in w.nodes],
        edges=[WorkflowEdgeOut(
            id=e.id, source_id=e.source_id, target_id=e.target_id,
            data=json.loads(e.data_json) if e.data_json else {},
        ) for e in w.edges],
    )


@router.get("", response_model=List[WorkflowSummary])
def list_workflows(include_archived: bool = False, db: Session = Depends(get_db)):
    q = db.query(Workflow)
    if not include_archived:
        q = q.filter(Workflow.archived == False)  # noqa: E712
    items = q.order_by(Workflow.updated_at.desc()).all()
    out = []
    for w in items:
        nc = db.query(WorkflowNode).filter_by(workflow_id=w.id).count()
        ec = db.query(WorkflowEdge).filter_by(workflow_id=w.id).count()
        out.append(WorkflowSummary(
            id=w.id, name=w.name, status=w.status, version=w.version, archived=w.archived,
            created_at=w.created_at, updated_at=w.updated_at,
            node_count=nc, edge_count=ec,
        ))
    return out


@router.post("", response_model=WorkflowOut)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    w = Workflow(
        name=payload.name, status=payload.status, version=payload.version, archived=payload.archived,
        viewport_json=json.dumps(payload.viewport) if payload.viewport else None,
    )
    db.add(w)
    db.flush()
    for n in payload.nodes:
        nid = n.id or WorkflowNode(id=WorkflowNode().id).id
        db.add(WorkflowNode(
            id=nid, workflow_id=w.id, type=n.type, position_x=n.position_x, position_y=n.position_y,
            width=n.width, height=n.height, parent_id=n.parent_id, hidden=n.hidden,
            data_json=json.dumps(n.data),
        ))
    for e in payload.edges:
        eid = e.id or WorkflowEdge(id=WorkflowEdge().id).id
        db.add(WorkflowEdge(
            id=eid, workflow_id=w.id, source_id=e.source_id, target_id=e.target_id,
            data_json=json.dumps(e.data),
        ))
    db.commit()
    db.refresh(w)
    return _to_out(w)


@router.get("/{wid}", response_model=WorkflowOut)
def get_workflow(wid: str, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter(Workflow.id == wid).first()
    if not w:
        raise HTTPException(404, "Workflow not found")
    return _to_out(w)


@router.put("/{wid}", response_model=WorkflowOut)
def update_workflow(wid: str, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter(Workflow.id == wid).first()
    if not w:
        raise HTTPException(404, "Workflow not found")
    if payload.name is not None:
        w.name = payload.name
    if payload.status is not None:
        w.status = payload.status
    if payload.archived is not None:
        w.archived = payload.archived
    if payload.viewport is not None:
        w.viewport_json = json.dumps(payload.viewport)
    w.version += 1
    db.commit()
    db.refresh(w)
    return _to_out(w)


@router.delete("/{wid}")
def delete_workflow(wid: str, db: Session = Depends(get_db)):
    w = db.query(Workflow).filter(Workflow.id == wid).first()
    if not w:
        raise HTTPException(404, "Workflow not found")
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.post("/{wid}/clone", response_model=WorkflowOut)
def clone_workflow(wid: str, db: Session = Depends(get_db)):
    src = db.query(Workflow).filter(Workflow.id == wid).first()
    if not src:
        raise HTTPException(404, "Workflow not found")
    # Deep copy via the same logic
    payload = WorkflowCreate(
        name=f"{src.name} (copy)", status="draft", version=1, archived=False,
        viewport=json.loads(src.viewport_json) if src.viewport_json else None,
    )
    return create_workflow(payload, db)


@router.put("/{wid}/save")
def save_workflow_full(wid: str, payload: WorkflowCreate, db: Session = Depends(get_db)):
    """Save all nodes & edges (replaces)."""
    w = db.query(Workflow).filter(Workflow.id == wid).first()
    if not w:
        raise HTTPException(404, "Workflow not found")
    w.name = payload.name
    w.status = payload.status
    if payload.viewport is not None:
        w.viewport_json = json.dumps(payload.viewport)
    w.version += 1

    db.query(WorkflowNode).filter_by(workflow_id=wid).delete()
    db.query(WorkflowEdge).filter_by(workflow_id=wid).delete()

    for n in payload.nodes:
        nid = n.id or WorkflowNode(id=WorkflowNode().id).id
        db.add(WorkflowNode(
            id=nid, workflow_id=wid, type=n.type, position_x=n.position_x, position_y=n.position_y,
            width=n.width, height=n.height, parent_id=n.parent_id, hidden=n.hidden,
            data_json=json.dumps(n.data),
        ))
    for e in payload.edges:
        eid = e.id or WorkflowEdge(id=WorkflowEdge().id).id
        db.add(WorkflowEdge(
            id=eid, workflow_id=wid, source_id=e.source_id, target_id=e.target_id,
            data_json=json.dumps(e.data),
        ))
    db.commit()
    return {"ok": True, "version": w.version}


# --- Snapshots ---

@router.get("/{wid}/snapshots", response_model=List[SnapshotOut])
def list_snapshots(wid: str, db: Session = Depends(get_db)):
    items = db.query(WorkflowSnapshot).filter_by(workflow_id=wid).order_by(WorkflowSnapshot.created_at.desc()).all()
    out = []
    for s in items:
        try:
            nodes = json.loads(s.nodes_json)
            edges = json.loads(s.edges_json)
        except Exception:
            nodes, edges = [], []
        out.append(SnapshotOut(
            id=s.id, workflow_id=s.workflow_id, label=s.label, created_at=s.created_at,
            node_count=len(nodes), edge_count=len(edges),
        ))
    return out


@router.post("/{wid}/snapshots", response_model=SnapshotOut)
def create_snapshot(wid: str, payload: SnapshotCreate, db: Session = Depends(get_db)):
    s = WorkflowSnapshot(
        workflow_id=wid, label=payload.label,
        nodes_json=json.dumps([n if isinstance(n, dict) else n.__dict__ for n in payload.nodes]),
        edges_json=json.dumps([e if isinstance(e, dict) else e.__dict__ for e in payload.edges]),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return SnapshotOut(
        id=s.id, workflow_id=s.workflow_id, label=s.label, created_at=s.created_at,
        node_count=len(payload.nodes), edge_count=len(payload.edges),
    )


@router.post("/{wid}/snapshots/{sid}/restore", response_model=WorkflowOut)
def restore_snapshot(wid: str, sid: str, db: Session = Depends(get_db)):
    s = db.query(WorkflowSnapshot).filter_by(id=sid, workflow_id=wid).first()
    if not s:
        raise HTTPException(404, "Snapshot not found")
    nodes = json.loads(s.nodes_json)
    edges = json.loads(s.edges_json)
    # Use the save_workflow_full logic
    w = db.query(Workflow).filter(Workflow.id == wid).first()
    if not w:
        raise HTTPException(404, "Workflow not found")
    db.query(WorkflowNode).filter_by(workflow_id=wid).delete()
    db.query(WorkflowEdge).filter_by(workflow_id=wid).delete()
    for n in nodes:
        db.add(WorkflowNode(
            id=n.get("id") or WorkflowNode(id=WorkflowNode().id).id,
            workflow_id=wid,
            type=n.get("type", "task"),
            position_x=n.get("position", {}).get("x", 0),
            position_y=n.get("position", {}).get("y", 0),
            width=n.get("width"), height=n.get("height"),
            parent_id=n.get("parentId"),
            hidden=n.get("hidden", False),
            data_json=json.dumps(n.get("data", {})),
        ))
    for e in edges:
        db.add(WorkflowEdge(
            id=e.get("id") or WorkflowEdge(id=WorkflowEdge().id).id,
            workflow_id=wid,
            source_id=e.get("source"),
            target_id=e.get("target"),
            data_json=json.dumps(e.get("data", {})),
        ))
    w.version += 1
    db.commit()
    db.refresh(w)
    return _to_out(w)


@router.delete("/{wid}/snapshots/{sid}")
def delete_snapshot(wid: str, sid: str, db: Session = Depends(get_db)):
    s = db.query(WorkflowSnapshot).filter_by(id=sid, workflow_id=wid).first()
    if not s:
        raise HTTPException(404, "Snapshot not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


# --- Action options (custom actions used in workflow nodes) ---

actions_router = APIRouter(prefix="/api/actions", tags=["actions"])


@actions_router.get("", response_model=List[ActionOptionOut])
def list_actions(db: Session = Depends(get_db)):
    return db.query(ActionOption).order_by(ActionOption.name).all()


@actions_router.post("", response_model=ActionOptionOut)
def add_action(name: str, db: Session = Depends(get_db)):
    name = name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    if db.query(ActionOption).filter_by(name=name).first():
        raise HTTPException(409, "Action already exists")
    a = ActionOption(name=name)
    db.add(a)
    db.commit()
    return a


@actions_router.put("/{name}", response_model=List[ActionOptionOut])
def rename_action(name: str, new_name: str, db: Session = Depends(get_db)):
    a = db.query(ActionOption).filter_by(name=name).first()
    if not a:
        raise HTTPException(404, "Action not found")
    new_name = new_name.strip()
    if not new_name:
        raise HTTPException(400, "Name required")
    a.name = new_name
    db.commit()
    return list_actions(db)


@actions_router.delete("/{name}")
def delete_action(name: str, db: Session = Depends(get_db)):
    a = db.query(ActionOption).filter_by(name=name).first()
    if not a:
        raise HTTPException(404, "Action not found")
    db.delete(a)
    db.commit()
    return {"ok": True}
