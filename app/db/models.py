from sqlalchemy import Column, ForeignKey, String, DateTime, Table, Enum, Text, BigInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base

# Association tables
service_incident_association = Table(
    "service_incident_association",
    Base.metadata,
    Column("service_id", BigInteger, ForeignKey("services.service_id")),
    Column("incident_id", BigInteger, ForeignKey("incidents.incident_id")),
)

# Enums
class ServiceStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    MAINTENANCE = "maintenance"


class IncidentStatus(str, enum.Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class IncidentImpact(str, enum.Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"

IMPACT_PRIORITY = {
    IncidentImpact.MINOR: 1,
    IncidentImpact.MAJOR: 2,
    IncidentImpact.CRITICAL: 3,
}

# Models
class Organization(Base):
    __tablename__ = "organizations"

    organization_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    auth0_org_id = Column(String, unique=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    auth0_id = Column(String, unique=True, index=True, nullable=False)  # User ID from Auth0
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    incident_updates = relationship("IncidentUpdate", back_populates="created_by")
    status_history = relationship("StatusHistory", back_populates="created_by")


class Service(Base):
    __tablename__ = "services"

    service_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"), nullable=False)
    current_status = Column(Enum(ServiceStatus), default=ServiceStatus.OPERATIONAL, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    incidents = relationship("Incident", secondary=service_incident_association, back_populates="affected_services")
    status_history = relationship("StatusHistory", back_populates="service", cascade="all, delete-orphan")


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"), nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.INVESTIGATING, nullable=False)
    impact = Column(Enum(IncidentImpact), default=IncidentImpact.MINOR, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    affected_services = relationship("Service", secondary=service_incident_association, back_populates="incidents")
    updates = relationship("IncidentUpdate", back_populates="incident", cascade="all, delete-orphan")


class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    incident_update_id = Column(BigInteger, primary_key=True, autoincrement=True)
    incident_id = Column(BigInteger, ForeignKey("incidents.incident_id"), nullable=False)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(IncidentStatus), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    # Relationships
    incident = relationship("Incident", back_populates="updates")
    created_by = relationship("User", back_populates="incident_updates")


class StatusHistory(Base):
    __tablename__ = "status_history"

    status_history_id = Column(BigInteger, primary_key=True, autoincrement=True)
    service_id = Column(BigInteger, ForeignKey("services.service_id"), nullable=False)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"), nullable=False)
    status = Column(Enum(ServiceStatus), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    # Relationships
    service = relationship("Service", back_populates="status_history")
    created_by = relationship("User", back_populates="status_history")
