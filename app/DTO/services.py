from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.db.models import ServiceStatus


class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class ServiceCreate(ServiceBase):
    current_status: ServiceStatus = ServiceStatus.OPERATIONAL


class ServiceUpdate(ServiceBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    current_status: Optional[ServiceStatus] = None


class ServiceStatusUpdate(BaseModel):
    status: ServiceStatus
    message: Optional[str] = Field(None, max_length=500)


class StatusHistoryResponse(BaseModel):
    status_history_id: int
    status: ServiceStatus
    created_at: datetime
    created_by_name: str

    class Config:
        from_attributes = True


class ServiceResponse(BaseModel):
    service_id: int
    name: str
    description: Optional[str]
    current_status: ServiceStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ServiceWithHistoryResponse(ServiceResponse):
    status_history: List[StatusHistoryResponse] = []
    uptime_percentage: Optional[float] = None
