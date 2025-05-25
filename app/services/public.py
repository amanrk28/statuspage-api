from collections import defaultdict
from typing import Tuple, List, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.DTO.incident import IncidentRead
from app.DTO.organization import OrganizationResponse
from app.db import Service, Incident, StatusHistory, IncidentUpdate
from app.db.database import get_db
from app.db.models import Organization, ServiceStatus, service_incident_association, IncidentStatus
from app.DTO.public import PublicStatus, PublicService, PublicServiceHistoryResponse

from datetime import datetime, timedelta, timezone
from sqlalchemy import and_


class PublicStatusCRUD:
    def get_status(self, org_slug: str) -> PublicStatus:
        with get_db() as db:
            return self._build_status(db, org_slug)

    def _build_status(self, db: Session, org_slug: str) -> PublicStatus:
        org = self._get_organization(db, org_slug)
        services = self._get_services(db, org.organization_id)
        incidents_by_service = self._get_incidents_by_service(db, services, org.organization_id)
        history_map = self._get_status_history_map(db, org.organization_id)

        public_services = [
            self._build_public_service(db, service, history_map, incidents_by_service)
            for service in services
        ]

        incident_response = [IncidentRead.model_validate(i) for i in set(sum(incidents_by_service.values(), []))]

        return PublicStatus(
            public_services=public_services,
            incidents=incident_response,
            organization=OrganizationResponse(name=org.display_name, auth0_org_id=org.auth0_org_id),
        )

    def _get_organization(self, db: Session, slug: str) -> Organization:
        org = db.query(Organization).filter(Organization.name == slug, Organization.is_deleted == False).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org

    def _get_services(self, db: Session, org_id: int) -> List[Service]:
        services = db.query(Service).filter(Service.organization_id == org_id, Service.is_deleted == False).order_by(Service.service_id.desc()).all()
        return services

    def _get_incidents_by_service(self, db: Session, services: List[Service], org_id: int) -> Dict[int, List[Incident]]:
        service_ids = [s.service_id for s in services]
        incident_service_map = db.query(
            service_incident_association.c.service_id,
            Incident
        ).join(Incident, and_(Incident.incident_id == service_incident_association.c.incident_id, Incident.is_deleted == False)).filter(
            Incident.organization_id == org_id,
            Incident.status != IncidentStatus.RESOLVED,
            service_incident_association.c.service_id.in_(service_ids)
        ).order_by(Incident.created_at.desc()).all()

        service_to_incidents: Dict[int, List[Incident]] = defaultdict(list)
        for service_id, incident in incident_service_map:
            service_to_incidents[service_id].append(incident)

        return service_to_incidents

    def _get_status_history_map(self, db: Session, org_id: int) -> Dict[Tuple[int, datetime], List[StatusHistory]]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        entries = db.query(StatusHistory).filter(
            and_(
                StatusHistory.organization_id == org_id,
                StatusHistory.created_at >= start_date,
                StatusHistory.created_at <= end_date,
                StatusHistory.is_deleted == False,
            )
        ).order_by(StatusHistory.created_at).all()

        history_map: Dict[Tuple[int, datetime], List[StatusHistory]] = defaultdict(list)
        for entry in entries:
            key = (entry.service_id, entry.created_at.date())
            history_map[key].append(entry)

        return history_map

    def _build_public_service(
            self,
            db: Session,
            service: Service,
            history_map: Dict[Tuple[int, datetime], List[StatusHistory]],
            service_to_incidents: Dict[int, List[Incident]],
    ) -> PublicService:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        uptime_history: List[PublicServiceHistoryResponse] = []
        current_date = start_date

        while current_date <= end_date:
            key = (service.service_id, current_date.date())
            entries = history_map.get(key, [])
            downtime_seconds, status = self.calculate_service_downtime(service.service_id, entries, current_date)
            uptime_history.append(PublicServiceHistoryResponse(
                date=current_date.date(),
                downtime_seconds=downtime_seconds,
                status=status
            ))
            current_date += timedelta(days=1)

        latest_message, latest_status = None, None
        if service.current_status != ServiceStatus.OPERATIONAL:
            incidents = service_to_incidents.get(service.service_id, [])
            if incidents:
                latest = incidents[0]  # Already sorted by created_at desc
                latest_status = latest.status

                # Try to get the latest incident update message if it exists
                latest_update = db.query(IncidentUpdate).filter(
                    IncidentUpdate.incident_id == latest.incident_id,
                    IncidentUpdate.is_deleted == False,
                ).order_by(IncidentUpdate.created_at.desc()).first()

                if latest_update:
                    latest_message = latest_update.message
                else:
                    latest_message = latest.description

        return PublicService(
            id=service.service_id,
            name=service.name,
            description=service.description,
            current_status=service.current_status,
            uptime_history=uptime_history,
            latest_incident_message=latest_message,
            latest_incident_status=latest_status
        )

    def calculate_service_downtime(
            self,
            service_id: int,
            day_entries: List[StatusHistory],
            current_date: datetime
    ) -> Tuple[float, ServiceStatus]:
        """
        Calculates total downtime in seconds for a given service on a specific day.
        """
        if not day_entries:
            return 0.0, ServiceStatus.OPERATIONAL

        day_start = datetime.combine(current_date.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = datetime.now(timezone.utc)

        total_downtime = timedelta()
        prev_time = day_start
        current_status = ServiceStatus.OPERATIONAL
        downtime_active = False

        for entry in day_entries:
            if downtime_active:
                total_downtime += entry.created_at - prev_time

            downtime_active = entry.status != ServiceStatus.OPERATIONAL
            if downtime_active:
                current_status = entry.status

            prev_time = entry.created_at

        # Handle trailing downtime until end of day
        if downtime_active:
            total_downtime += day_end - prev_time

        return round(total_downtime.total_seconds(), 2), current_status
