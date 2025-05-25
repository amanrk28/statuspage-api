from datetime import datetime, timezone

from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.DTO.incident import IncidentRead, IncidentUpdateRead, IncidentResponse, IncidentUpdateRequest, IncidentCreate, \
    IncidentUpdateCreate
from app.DTO.services import ServiceResponse
from app.DTO.status_history import StatusHistoryCreate
from app.core.objects import Object, Event
from app.db import StatusHistory, Organization
from app.db.database import get_db
from app.db.models import Incident, IncidentUpdate, Service, IncidentImpact, ServiceStatus, User, IncidentStatus, \
    IMPACT_PRIORITY
from typing import Optional, List

from app.services.services import ServiceCRUD
from app.websocket.websockets import broadcast

service_crud = ServiceCRUD()


class IncidentService(ServiceCRUD):
    def __init__(self):
        super().__init__()

    def _status_for_impact(self, impact: IncidentImpact) -> ServiceStatus:
        if impact == IncidentImpact.CRITICAL:
            return ServiceStatus.MAJOR_OUTAGE
        elif impact == IncidentImpact.MAJOR:
            return ServiceStatus.PARTIAL_OUTAGE
        elif impact == IncidentImpact.MINOR:
            return ServiceStatus.DEGRADED
        return ServiceStatus.OPERATIONAL

    # Incident CRUD
    def create_incident(self, data: IncidentCreate, user: User, organization: Organization,
                        background_tasks: BackgroundTasks) -> IncidentRead:
        with get_db() as db:
            incident = Incident(
                title=data.title,
                description=data.description,
                organization_id=organization.organization_id,
                status=data.status,
                impact=data.impact,
            )

            db.add(incident)
            db.flush()

            if data.affected_service_ids:
                affected_services = db.query(Service).filter(
                    Service.organization_id == organization.organization_id,
                    Service.service_id.in_(data.affected_service_ids),
                    Service.is_deleted == False,
                ).all()

                for service in affected_services:
                    incident.affected_services.append(service)

                    new_status = self._status_for_impact(data.impact)
                    db.add(StatusHistory(
                        service_id=service.service_id,
                        organization_id=organization.organization_id,
                        status=new_status,
                        created_by_id=user.user_id,
                    ))

                    service.current_status = new_status

                    # Broadcast real-time update
                    background_tasks.add_task(
                        broadcast,
                        organization=organization,
                        object=Object.SERVICE,
                        event=Event.STATUS_UPDATED,
                        data={
                            "service_id": str(service.service_id),
                            "name": service.name,
                            "new_status": new_status.value,
                            "updated_by": user.name,
                        }
                    )

            db.commit()
            db.refresh(incident)
            return IncidentRead(
                incident_id=incident.incident_id,
                title=incident.title,
                description=incident.description,
                status=incident.status,
                impact=incident.impact,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
                resolved_at=incident.resolved_at,
            )

    def get_incident(self, incident_id: int, user: User, organization: Organization) -> IncidentResponse:
        with get_db() as db:
            incident = db.query(Incident).filter(
                Incident.organization_id == organization.organization_id).filter(
                Incident.incident_id == incident_id,
                Incident.is_deleted == False).first()

            if not incident:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

            return IncidentResponse(
                incident_id=incident.incident_id,
                title=incident.title,
                description=incident.description,
                status=incident.status,
                impact=incident.impact,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
                resolved_at=incident.resolved_at,
                affected_services=[
                    ServiceResponse.model_validate(service)
                    for service in incident.affected_services
                ]
            )

    def get_all_incidents(self, resolved: str, user: User, organization: Organization) -> List[IncidentRead]:
        with (get_db() as db):
            status_filter = 1 == 1

            if resolved == 'true':
                status_filter = Incident.status == IncidentStatus.RESOLVED
            elif resolved == 'false':
                status_filter = Incident.status.not_in([IncidentStatus.RESOLVED])

            incidents = db.query(Incident).order_by(Incident.created_at.desc()).filter(
                Incident.organization_id == organization.organization_id, status_filter,
                Incident.is_deleted == False).all()

            return [IncidentRead.model_validate(i) for i in incidents]

    def update_incident(self, incident_id: int, updates: IncidentUpdateRequest, user: User,
                        organization: Organization,
                        background_tasks: BackgroundTasks) -> Optional[IncidentRead]:
        with get_db() as db:
            incident = db.query(Incident).filter(
                Incident.organization_id == organization.organization_id).filter(
                Incident.incident_id == incident_id,
                Incident.is_deleted == False).first()

            if not incident:
                return None

            for field, value in updates.model_dump(exclude_unset=True).items():
                if field == "service_ids" and value is not None:
                    incident.affected_services = db.query(Service).filter(
                        Service.organization_id == organization.organization_id, Service.service_id.in_(value),
                        Incident.is_deleted == False).all()
                elif field == "impact" and value is not None:
                    setattr(incident, field, value)
                    new_status = self._status_for_impact(value)

                    # If the incident is not resolved, then update status for affected services
                    if not incident.status == IncidentStatus.RESOLVED:
                        for service in incident.affected_services:
                            # Check for other incidents still affecting this service
                            other_incidents = db.query(Incident).join(Incident.affected_services).filter(
                                Incident.organization_id == organization.organization_id,
                                Incident.incident_id != incident.incident_id,
                                Incident.status != IncidentStatus.RESOLVED,
                                Service.service_id == service.service_id,
                                Incident.is_deleted == False
                            ).all()

                            # Check if any of the other incidents have equal or higher impact
                            has_conflict = any(
                                IMPACT_PRIORITY[other.impact] >= IMPACT_PRIORITY[value]
                                for other in other_incidents
                            )

                            if not has_conflict:
                                service.current_status = new_status

                                status_data = StatusHistoryCreate(
                                    service_id=service.service_id,
                                    status=new_status
                                )
                                service_crud.create_status_history(status_data, user, organization)

                elif field == "status" and value is not None and value == IncidentStatus.RESOLVED:
                    setattr(incident, field, value)
                    setattr(incident, 'resolved_at', datetime.now(tz=timezone.utc))

                    self._reconcile_affected_services(db, incident, user, organization)
                else:
                    setattr(incident, field, value)

            db.commit()
            db.refresh(incident)

            # Broadcast real-time update
            background_tasks.add_task(
                broadcast,
                organization=organization,
                object=Object.SERVICE,
                event=Event.BULK_UPDATED,
                data={
                    "service_ids": ",".join([str(s.service_id) for s in incident.affected_services]),
                    "updated_by": user.name,
                }
            )

            return IncidentRead(
                incident_id=incident.incident_id,
                title=incident.title,
                description=incident.description,
                status=incident.status,
                impact=incident.impact,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
                resolved_at=incident.resolved_at,
            )

    def delete_incident(self, incident_id: int, user: User, organization: Organization,
                        background_tasks: BackgroundTasks):
        with get_db() as db:
            incident = db.query(Incident).filter(
                Incident.organization_id == organization.organization_id).filter(
                Incident.incident_id == incident_id,
                Incident.is_deleted == False,
            ).first()
            if not incident:
                return False

            self._reconcile_affected_services(db, incident, user, organization)

            # Soft delete instead of hard delete
            incident.is_deleted = True
            incident.updated_at = datetime.now()
            db.commit()

            # Broadcast real-time update
            background_tasks.add_task(
                broadcast,
                organization,
                object=Object.INCIDENT,
                event=Event.DELETED,
                data={
                    "service_id": str(incident.incident_id),
                    "name": incident.title,
                }
            )

            return True

    def _reconcile_affected_services(self, db: Session, incident: Incident, user: User, organization: Organization):
        # Mark all affected services as operational
        for service in incident.affected_services:
            # Check for other active incidents affecting this service
            other_active_incidents = db.query(Incident).join(Incident.affected_services).filter(
                Incident.organization_id == organization.organization_id,
                Incident.status != IncidentStatus.RESOLVED,
                Incident.incident_id != incident.incident_id,
                Service.service_id == service.service_id,
                Incident.is_deleted == False
            ).all()

            # If no other active incidents, mark the service as OPERATIONAL
            if not other_active_incidents:
                service.current_status = ServiceStatus.OPERATIONAL

                status_data = StatusHistoryCreate(
                    service_id=service.service_id,
                    status=ServiceStatus.OPERATIONAL
                )
                service_crud.create_status_history(status_data, user, organization)

    # IncidentUpdate CRUD
    def create_incident_update(self, data: IncidentUpdateCreate, user: User,
                               organization: Organization, background_tasks: BackgroundTasks) -> IncidentUpdateRead:
        with get_db() as db:
            incident = db.query(Incident).filter(Incident.organization_id == organization.organization_id,
                                                 Incident.incident_id == data.incident_id,
                                                 Incident.is_deleted == False).first()
            if not incident:
                raise HTTPException(status_code=404, detail="Incident not found")

            if incident.status == IncidentStatus.RESOLVED:
                raise HTTPException(status_code=400, detail="Cannot create incident update for resolved incidents")

            update = IncidentUpdate(
                incident_id=incident.incident_id,
                organization_id=organization.organization_id,
                status=incident.status,
                message=data.message,
                created_by_id=user.user_id,
            )
            db.add(update)
            db.commit()
            db.refresh(update)

            background_tasks.add_task(
                broadcast,
                organization=organization,
                object=Object.INCIDENT_UPDATE,
                event=Event.CREATED,
                data={
                    "incident_id": incident.incident_id,
                    "status": incident.status,
                    "message": update.message,
                    "updated_by": user.name,
                }
            )

            return IncidentUpdateRead.model_validate(update)

    def get_incident_updates(self, incident_id: int, user: User, organization: Organization) -> List[
        IncidentUpdateRead]:
        with get_db() as db:
            incident_updates = db.query(IncidentUpdate).order_by(IncidentUpdate.created_at.desc()).filter(
                IncidentUpdate.organization_id == organization.organization_id,
                IncidentUpdate.incident_id == incident_id,
                Incident.is_deleted == False
            ).all()
            return [IncidentUpdateRead.model_validate(iu) for iu in incident_updates]
