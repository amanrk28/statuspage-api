from datetime import datetime

from pydantic import BaseModel

from app.db.models import ServiceStatus


class StatusHistoryRead(BaseModel):
    status_history_id: int
    service_id: int
    status: ServiceStatus
    created_at: datetime
    created_by_id: int

    class Config:
        from_attributes = True


class StatusHistoryCreate(BaseModel):
    service_id: int
    status: ServiceStatus

    class Config:
        from_attributes = True
