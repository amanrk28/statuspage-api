from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.DTO.services import ServiceResponse
from app.db.models import IncidentStatus, IncidentImpact


class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: IncidentStatus = IncidentStatus.INVESTIGATING
    impact: IncidentImpact = IncidentImpact.MINOR


class IncidentCreate(IncidentBase):
    affected_service_ids: Optional[List[int]] = Field(default_factory=list)


class IncidentUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[IncidentStatus] = None
    impact: Optional[IncidentImpact] = None
    resolved_at: Optional[datetime] = None
    service_ids: Optional[List[int]] = None


class IncidentRead(IncidentBase):
    incident_id: int
    created_at: datetime
    resolved_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class IncidentResponse(IncidentRead):
    affected_services: List[ServiceResponse] = Field(default_factory=list)

class IncidentUpdateBase(BaseModel):
    incident_id: int
    message: str


class IncidentUpdateCreate(IncidentUpdateBase):
    pass


class IncidentUpdateRead(IncidentUpdateBase):
    incident_update_id: int
    status: IncidentStatus
    created_by_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
