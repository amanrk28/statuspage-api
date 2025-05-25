import datetime
from typing import Optional
from pydantic import BaseModel

from app.DTO.incident import IncidentRead
from app.DTO.organization import OrganizationResponse
from app.db.models import ServiceStatus, IncidentStatus


class PublicServiceHistoryResponse(BaseModel):
    date: datetime.date
    downtime_seconds: float
    status: ServiceStatus

class PublicService(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    current_status: ServiceStatus
    latest_incident_message: Optional[str] = None
    latest_incident_status: Optional[IncidentStatus] = None
    uptime_history: list[PublicServiceHistoryResponse]


class PublicStatus(BaseModel):
    organization: OrganizationResponse
    public_services: list[PublicService]
    incidents: list[IncidentRead]