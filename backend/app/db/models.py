from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(64), default="citizen", nullable=False)  # citizen, farmer, officer, admin
    consent_alerts = Column(Boolean, default=False, nullable=False)  # DPDP consent flag
    phone_number = Column(String(255), nullable=True)  # Decoupled / pseudonymized identifier
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WeatherForecastRecord(Base):
    __tablename__ = "weather_forecast_records"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(64), nullable=False)  # 'IMD_PDF', 'OpenMeteo'
    ingestion_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_issue_time = Column(DateTime, nullable=False)
    transformation_history = Column(JSONB, default=list, nullable=False)  # Audit list of parsers
    data_payload = Column(JSONB, default=dict, nullable=False)  # Standardized weather metric grids


class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(64), nullable=False)  # district, river, reservoir, school, hospital, weather_event
    properties = Column(JSONB, default=dict, nullable=False)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)  # PostGIS Geometry type

    # Relationships
    outgoing_edges = relationship(
        "GraphEdge",
        foreign_keys="[GraphEdge.source_id]",
        back_populates="source_node",
        cascade="all, delete-orphan"
    )
    incoming_edges = relationship(
        "GraphEdge",
        foreign_keys="[GraphEdge.target_id]",
        back_populates="target_node",
        cascade="all, delete-orphan"
    )


class GraphEdge(Base):
    __tablename__ = "graph_edges"

    source_id = Column(String(64), ForeignKey("graph_nodes.id", ondelete="CASCADE"), primary_key=True)
    target_id = Column(String(64), ForeignKey("graph_nodes.id", ondelete="CASCADE"), primary_key=True)
    type = Column(String(64), primary_key=True)  # affects, located_in, downstream_of, connected_to
    properties = Column(JSONB, default=dict, nullable=False)

    # Node relationships
    source_node = relationship("GraphNode", foreign_keys=[source_id], back_populates="outgoing_edges")
    target_node = relationship("GraphNode", foreign_keys=[target_id], back_populates="incoming_edges")


class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    query = Column(String, nullable=False)
    response = Column(String, nullable=False)
    retrieval_precision = Column(Float, nullable=False)  # NDCG metric
    citation_accuracy = Column(Float, nullable=False)  # F1 token-matching score
    hallucination_rate = Column(Float, nullable=False)  # NLI confidence check
    response_latency = Column(Float, nullable=False)  # API processing duration
    confidence_score = Column(Float, nullable=False)  # Grounding confidence rating


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_ip = Column(String(64), nullable=False)
    user_id = Column(Integer, nullable=True)  # Nullable if unauthenticated
    requested_endpoint = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)  # Read, Write, Delete, Query
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    payload_hash = Column(String(255), nullable=False)  # IT Act 2000 write-only immutability proof
