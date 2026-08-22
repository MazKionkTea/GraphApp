"""All SQLAlchemy ORM models — one file, all 3 modes share the same DB."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _now() -> datetime:
    return datetime.utcnow()


def _id() -> str:
    import uuid
    return uuid.uuid4().hex[:16]


# =====================================================================
# MIND MAP
# =====================================================================

class Mindmap(Base):
    __tablename__ = "mindmaps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    theme: Mapped[str] = mapped_column(String, default="default")
    layout: Mapped[str] = mapped_column(String, default="free")  # lr | tb | radial | free
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    nodes: Mapped[List["MindmapNode"]] = relationship(back_populates="mindmap", cascade="all, delete-orphan")
    edges: Mapped[List["MindmapEdge"]] = relationship(back_populates="mindmap", cascade="all, delete-orphan")


class MindmapNode(Base):
    __tablename__ = "mindmap_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    mindmap_id: Mapped[str] = mapped_column(String, ForeignKey("mindmaps.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String, default="")
    icon: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pos_x: Mapped[float] = mapped_column(Float, default=0)
    pos_y: Mapped[float] = mapped_column(Float, default=0)
    parent_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("mindmap_nodes.id"), nullable=True)

    mindmap: Mapped[Mindmap] = relationship(back_populates="nodes")


class MindmapEdge(Base):
    __tablename__ = "mindmap_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    mindmap_id: Mapped[str] = mapped_column(String, ForeignKey("mindmaps.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("mindmap_nodes.id", ondelete="CASCADE"))
    target_id: Mapped[str] = mapped_column(String, ForeignKey("mindmap_nodes.id", ondelete="CASCADE"))
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    mindmap: Mapped[Mindmap] = relationship(back_populates="edges")


# =====================================================================
# WORKFLOW
# =====================================================================

class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | published
    version: Mapped[int] = mapped_column(Integer, default=1)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    viewport_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    nodes: Mapped[List["WorkflowNode"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    edges: Mapped[List["WorkflowEdge"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    snapshots: Mapped[List["WorkflowSnapshot"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String, default="task")  # task | group
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # arbitrary node data

    workflow: Mapped[Workflow] = relationship(back_populates="nodes")


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_nodes.id", ondelete="CASCADE"))
    target_id: Mapped[str] = mapped_column(String, ForeignKey("workflow_nodes.id", ondelete="CASCADE"))
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # label, color, waypoints, animated

    workflow: Mapped[Workflow] = relationship(back_populates="edges")


class WorkflowSnapshot(Base):
    __tablename__ = "workflow_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    workflow_id: Mapped[str] = mapped_column(String, ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    nodes_json: Mapped[str] = mapped_column(Text, nullable=False)
    edges_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    workflow: Mapped[Workflow] = relationship(back_populates="snapshots")


class ActionOption(Base):
    __tablename__ = "action_options"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# =====================================================================
# CODE PROJECTS (Code Graph mode)
# =====================================================================

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String, nullable=False)
    root_path: Mapped[str] = mapped_column(String, nullable=False)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    settings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    files: Mapped[List["CodeFile"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    symbols: Mapped[List["Symbol"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    calls: Mapped[List["Call"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    imports: Mapped[List["Import"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class CodeFile(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mtime: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    project: Mapped[Project] = relationship(back_populates="files")
    symbols: Mapped[List["Symbol"]] = relationship(back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("project_id", "path", name="uq_file_project_path"),)


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("files.id", ondelete="CASCADE"), index=True)
    fqn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # package|module|class|function|method
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_fqn: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    complexity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    loc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Phase 4 enriched
    fan_in: Mapped[int] = mapped_column(Integer, default=0)
    fan_out: Mapped[int] = mapped_column(Integer, default=0)
    total_calls: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    is_entry_point: Mapped[bool] = mapped_column(Boolean, default=False)
    is_leaf: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="symbols")
    file: Mapped[CodeFile] = relationship(back_populates="symbols")

    __table_args__ = (UniqueConstraint("project_id", "fqn", name="uq_symbol_project_fqn"),)


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_fqn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_fqn: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    call_count: Mapped[int] = mapped_column(Integer, default=1)
    total_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    source_type: Mapped[str] = mapped_column(String, default="project")  # project|external
    mode: Mapped[str] = mapped_column(String, default="static")  # static|dynamic

    project: Mapped[Project] = relationship(back_populates="calls")


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    module_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    imported_names_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(back_populates="imports")


# =====================================================================
# SETTINGS
# =====================================================================

class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
