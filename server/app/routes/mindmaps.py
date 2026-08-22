"""Mind Map CRUD routes."""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.db.models import Mindmap, MindmapNode, MindmapEdge
from app.schemas import (
    MindmapCreate, MindmapUpdate, MindmapOut, MindmapSummary,
    MindmapNodeCreate, MindmapNodeOut, MindmapEdgeCreate, MindmapEdgeOut,
)

router = APIRouter(prefix="/api/mindmaps", tags=["mindmaps"])


def _to_out(m: Mindmap) -> MindmapOut:
    return MindmapOut(
        id=m.id, name=m.name, theme=m.theme, layout=m.layout,
        created_at=m.created_at, updated_at=m.updated_at,
        nodes=[MindmapNodeOut.model_validate(n) for n in m.nodes],
        edges=[MindmapEdgeOut.model_validate(e) for e in m.edges],
    )


@router.get("", response_model=List[MindmapSummary])
def list_mindmaps(db: Session = Depends(get_db)):
    items = db.query(Mindmap).order_by(Mindmap.updated_at.desc()).all()
    out = []
    for m in items:
        nc = len(m.nodes) if m.nodes else db.query(MindmapNode).filter_by(mindmap_id=m.id).count()
        ec = len(m.edges) if m.edges else db.query(MindmapEdge).filter_by(mindmap_id=m.id).count()
        out.append(MindmapSummary(
            id=m.id, name=m.name, theme=m.theme, layout=m.layout,
            created_at=m.created_at, updated_at=m.updated_at,
            node_count=nc, edge_count=ec,
        ))
    return out


@router.post("", response_model=MindmapOut)
def create_mindmap(payload: MindmapCreate, db: Session = Depends(get_db)):
    m = Mindmap(name=payload.name, theme=payload.theme, layout=payload.layout)
    db.add(m)
    db.commit()
    db.refresh(m)
    return _to_out(m)


@router.get("/{mid}", response_model=MindmapOut)
def get_mindmap(mid: str, db: Session = Depends(get_db)):
    m = db.query(Mindmap).options(
        selectinload(Mindmap.nodes), selectinload(Mindmap.edges)
    ).filter(Mindmap.id == mid).first()
    if not m:
        raise HTTPException(404, "Mindmap not found")
    return _to_out(m)


@router.put("/{mid}", response_model=MindmapOut)
def update_mindmap(mid: str, payload: MindmapUpdate, db: Session = Depends(get_db)):
    m = db.query(Mindmap).filter(Mindmap.id == mid).first()
    if not m:
        raise HTTPException(404, "Mindmap not found")
    m.name = payload.name
    m.theme = payload.theme
    m.layout = payload.layout
    db.commit()
    db.refresh(m)
    return _to_out(m)


@router.delete("/{mid}")
def delete_mindmap(mid: str, db: Session = Depends(get_db)):
    m = db.query(Mindmap).filter(Mindmap.id == mid).first()
    if not m:
        raise HTTPException(404, "Mindmap not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


@router.put("/{mid}/nodes")
def replace_nodes(mid: str, nodes: List[MindmapNodeCreate], db: Session = Depends(get_db)):
    """Replace all nodes for a mindmap (called by autosave)."""
    m = db.query(Mindmap).filter(Mindmap.id == mid).first()
    if not m:
        raise HTTPException(404, "Mindmap not found")
    db.query(MindmapNode).filter_by(mindmap_id=mid).delete()
    for n in nodes:
        nid = n.id or MindmapNode(id=MindmapNode().id).id  # generate
        db.add(MindmapNode(
            id=nid, mindmap_id=mid, label=n.label, icon=n.icon, color=n.color,
            pos_x=n.pos_x, pos_y=n.pos_y, parent_id=n.parent_id,
        ))
    db.commit()
    return {"ok": True, "count": len(nodes)}


@router.put("/{mid}/edges")
def replace_edges(mid: str, edges: List[MindmapEdgeCreate], db: Session = Depends(get_db)):
    m = db.query(Mindmap).filter(Mindmap.id == mid).first()
    if not m:
        raise HTTPException(404, "Mindmap not found")
    db.query(MindmapEdge).filter_by(mindmap_id=mid).delete()
    for e in edges:
        eid = e.id or MindmapEdge(id=MindmapEdge().id).id
        db.add(MindmapEdge(
            id=eid, mindmap_id=mid, source_id=e.source_id, target_id=e.target_id, label=e.label,
        ))
    db.commit()
    return {"ok": True, "count": len(edges)}
