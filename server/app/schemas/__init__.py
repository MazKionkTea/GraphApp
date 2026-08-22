"""Pydantic schemas for request/response."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


# =====================================================================
# Common
# =====================================================================

class HealthResponse(BaseModel):
    ok: bool
    version: str


# =====================================================================
# Mind Map
# =====================================================================

class MindmapNodeBase(BaseModel):
    label: str = ""
    icon: Optional[str] = None
    color: Optional[str] = None
    pos_x: float = 0
    pos_y: float = 0
    parent_id: Optional[str] = None


class MindmapNodeCreate(MindmapNodeBase):
    id: Optional[str] = None


class MindmapNodeUpdate(MindmapNodeBase):
    pass


class MindmapNodeOut(MindmapNodeBase):
    id: str

    class Config:
        from_attributes = True


class MindmapEdgeBase(BaseModel):
    source_id: str
    target_id: str
    label: Optional[str] = None


class MindmapEdgeCreate(MindmapEdgeBase):
    id: Optional[str] = None


class MindmapEdgeOut(MindmapEdgeBase):
    id: str

    class Config:
        from_attributes = True


class MindmapBase(BaseModel):
    name: str
    theme: str = "default"
    layout: Literal["lr", "tb", "radial", "free"] = "free"


class MindmapCreate(MindmapBase):
    pass


class MindmapUpdate(MindmapBase):
    pass


class MindmapOut(MindmapBase):
    id: str
    created_at: datetime
    updated_at: datetime
    nodes: List[MindmapNodeOut] = []
    edges: List[MindmapEdgeOut] = []

    class Config:
        from_attributes = True


class MindmapSummary(BaseModel):
    id: str
    name: str
    theme: str
    layout: str
    created_at: datetime
    updated_at: datetime
    node_count: int = 0
    edge_count: int = 0

    class Config:
        from_attributes = True


# =====================================================================
# Workflow
# =====================================================================

class WorkflowNodeBase(BaseModel):
    type: str = "task"
    position_x: float = 0
    position_y: float = 0
    width: Optional[float] = None
    height: Optional[float] = None
    parent_id: Optional[str] = None
    hidden: bool = False
    data: Dict[str, Any] = Field(default_factory=dict)


class WorkflowNodeCreate(WorkflowNodeBase):
    id: Optional[str] = None


class WorkflowNodeOut(WorkflowNodeBase):
    id: str

    class Config:
        from_attributes = True


class WorkflowEdgeBase(BaseModel):
    source_id: str
    target_id: str
    data: Dict[str, Any] = Field(default_factory=dict)


class WorkflowEdgeCreate(WorkflowEdgeBase):
    id: Optional[str] = None


class WorkflowEdgeOut(WorkflowEdgeBase):
    id: str

    class Config:
        from_attributes = True


class WorkflowBase(BaseModel):
    name: str
    status: Literal["draft", "published"] = "draft"
    version: int = 1
    archived: bool = False
    viewport: Optional[Dict[str, Any]] = None


class WorkflowCreate(WorkflowBase):
    nodes: List[WorkflowNodeCreate] = []
    edges: List[WorkflowEdgeCreate] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[Literal["draft", "published"]] = None
    archived: Optional[bool] = None
    viewport: Optional[Dict[str, Any]] = None


class WorkflowOut(WorkflowBase):
    id: str
    created_at: datetime
    updated_at: datetime
    nodes: List[WorkflowNodeOut] = []
    edges: List[WorkflowEdgeOut] = []

    class Config:
        from_attributes = True


class WorkflowSummary(BaseModel):
    id: str
    name: str
    status: str
    version: int
    archived: bool
    created_at: datetime
    updated_at: datetime
    node_count: int = 0
    edge_count: int = 0

    class Config:
        from_attributes = True


class SnapshotCreate(BaseModel):
    label: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class SnapshotOut(BaseModel):
    id: str
    workflow_id: str
    label: str
    created_at: datetime
    node_count: int
    edge_count: int

    class Config:
        from_attributes = True


class ActionOptionOut(BaseModel):
    name: str

    class Config:
        from_attributes = True


# =====================================================================
# Code Project (Code Graph)
# =====================================================================

class ProjectCreate(BaseModel):
    name: str
    root_path: str


class ProjectSummary(BaseModel):
    id: str
    name: str
    root_path: str
    last_indexed_at: Optional[datetime]
    created_at: datetime
    file_count: int = 0
    symbol_count: int = 0
    call_count: int = 0

    class Config:
        from_attributes = True


class ProjectOut(ProjectSummary):
    settings: Dict[str, Any] = Field(default_factory=dict)


class IndexRequest(BaseModel):
    include_external: bool = True
    project_only_edges: bool = False
    dynamic_trace: bool = False
    target_script: Optional[str] = None


class IndexResult(BaseModel):
    project_id: str
    duration_seconds: float
    summary: Dict[str, Any]


class SymbolOut(BaseModel):
    id: str
    fqn: str
    name: str
    kind: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    parent_fqn: Optional[str] = None
    complexity: Optional[int] = None
    loc: Optional[int] = None
    fan_in: int = 0
    fan_out: int = 0
    total_calls: int = 0
    is_entry_point: bool = False
    is_leaf: bool = False

    class Config:
        from_attributes = True


class CallOut(BaseModel):
    id: str
    source_fqn: str
    target_fqn: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    call_count: int = 1
    source_type: str = "project"
    mode: str = "static"

    class Config:
        from_attributes = True


class FileOut(BaseModel):
    id: str
    path: str
    hash: Optional[str] = None

    class Config:
        from_attributes = True


class GraphData(BaseModel):
    """Unified graph response for Code Graph mode."""
    nodes: List[SymbolOut]
    edges: List[CallOut]
    summary: Dict[str, Any]
