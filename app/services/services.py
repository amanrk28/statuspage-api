from collections import defaultdict
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from app.DTO.status_history import StatusHistoryCreate, StatusHistoryRead
from app.core.objects import Object, Event
from app.db import Organization
from app.db.database import get_db
from app.db.models import Service, User, StatusHistory, ServiceStatus
from app.DTO.services import ServiceCreate, ServiceUpdate, ServiceStatusUpdate, ServiceResponse, \
    ServiceWithHistoryResponse, StatusHistoryResponse

from app.websocket.websockets import broadcast


class ServiceCRUD:
    def get_services(
            self,
            user: User,
            organization: Organization
    ) -> List[ServiceWithHistoryResponse]:
        """Get services for user's organization"""
        with get_db() as db:
            ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
            now = datetime.now(timezone.utc)

            services = db.query(Service).order_by(Service.service_id.desc()).filter(
                Service.organization_id == organization.organization_id,
                Service.is_deleted == False).all()

            service_ids = [s.service_id for s in services]
            history_rows = db.query(StatusHistory).filter(
                StatusHistory.service_id.in_(service_ids),
                StatusHistory.created_at >= ninety_days_ago,
                StatusHistory.is_deleted == False,
            ).order_by(StatusHistory.service_id, StatusHistory.created_at).all()

            history_by_service = defaultdict(list)
            for row in history_rows:
                history_by_service[row.service_id].append(row)

            service_responses = []
            for service in services:

                # Get status history within the last 90 days
                history = history_by_service.get(service.service_id, [])

                # Ensure timeline starts at 90 days ago
                if not history or history[0].created_at > ninety_days_ago:
                    history.insert(0, StatusHistory(
                        status=service.current_status,
                        created_at=ninety_days_ago
                    ))

                # Ensure timeline ends at now
                history.append(StatusHistory(status=service.current_status, created_at=now))

                # Calculate downtime
                total_downtime = timedelta(0)
                for i in range(len(history) - 1):
                    curr, next_ = history[i], history[i + 1]
                    if curr.status != ServiceStatus.OPERATIONAL:
                        total_downtime += (next_.created_at - curr.created_at)

                uptime_duration = timedelta(days=90) - total_downtime
                uptime_percentage = float(
                    f"{(uptime_duration.total_seconds() / timedelta(days=90).total_seconds()) * 100:.2f}")

                service_responses.append(ServiceWithHistoryResponse(
                    service_id=service.service_id,
                    name=service.name,
                    description=service.description,
                    current_status=service.current_status,
                    created_at=service.created_at,
                    updated_at=service.updated_at,
                    uptime_percentage=uptime_percentage,
                ))

            return service_responses

    def get_service(self, service_id: int, user: User, organization: Organization, background_tasks: BackgroundTasks) -> \
            Optional[ServiceWithHistoryResponse]:
        """Get service by ID if user has access"""
        with get_db() as db:
            service = db.query(Service).filter(
                Service.service_id == service_id,
                Service.organization_id == organization.organization_id,
                Service.is_deleted == False,
            ).options(
                joinedload(Service.status_history).joinedload(StatusHistory.created_by)
            ).first()

            if not service:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Service not found"
                )

            # Get status history
            status_history = []
            for history in service.status_history[-10:]:  # Last 10 entries
                status_history.append(StatusHistoryResponse(
                    status_history_id=history.status_history_id,
                    status=history.status,
                    created_at=history.created_at,
                    created_by_name=history.created_by.name,
                ))

            status_history = sorted(status_history, key=lambda h: h.created_at, reverse=True)

            uptime_percentage = self.get_service_uptime(service_id=service_id, user=user, organization=organization)

            return ServiceWithHistoryResponse(
                service_id=service.service_id,
                name=service.name,
                description=service.description,
                current_status=service.current_status,
                created_at=service.created_at,
                updated_at=service.updated_at,
                status_history=status_history,
                uptime_percentage=uptime_percentage
            )

    def create_service(self, service_in: ServiceCreate, user: User, organization: Organization,
                       background_tasks: BackgroundTasks) -> Optional[
        ServiceResponse]:
        """Create a new service"""
        # Create service
        with get_db() as db:
            service = Service(
                name=service_in.name,
                description=service_in.description,
                current_status=service_in.current_status,
                organization_id=organization.organization_id,
                created_at=datetime.now(),
            )

            db.add(service)
            db.flush()

            # Create initial status history entry
            status_history = StatusHistory(
                service_id=service.service_id,
                organization_id=organization.organization_id,
                status=service_in.current_status,
                created_by_id=user.user_id,
                created_at=datetime.now(),
            )
            db.add(status_history)

            db.commit()
            db.refresh(service)

            service_response = ServiceResponse(
                service_id=service.service_id,
                name=service.name,
                description=service.description,
                current_status=service.current_status,
                created_at=service.created_at,
                updated_at=service.updated_at
            )

            # Broadcast real-time update
            background_tasks.add_task(
                broadcast,
                organization=organization,
                object=Object.SERVICE,
                event=Event.CREATED,
                data={
                    "service_id": str(service.service_id),
                    "name": service.name,
                    "status": service.current_status,
                }
            )

            return service_response

    def update_service(
            self,
            service_id: int,
            service_in: ServiceUpdate,
            user: User,
            organization: Organization,
            background_tasks: BackgroundTasks
    ) -> Optional[ServiceResponse]:
        """Update service details"""
        with get_db() as db:
            service = db.query(Service).filter(
                Service.service_id == service_id,
                Service.organization_id == organization.organization_id,
                Service.is_deleted == False,
            ).first()

            if not service:
                return None

            # Update fields
            update_data = service_in.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(service, field, value)

            db.commit()
            db.refresh(service)

            # Broadcast real-time update
            background_tasks.add_task(
                broadcast,
                organization=organization,
                object=Object.SERVICE,
                event=Event.STATUS_UPDATED,
                data={
                    "service_id": str(service.service_id),
                    "name": service.name,
                    "updated_by": user.name,
                }
            )

            return ServiceResponse(
                service_id=service.service_id,
                name=service.name,
                description=service.description,
                current_status=service.current_status,
                created_at=service.created_at,
                updated_at=service.updated_at
            )

    def update_service_status(
            self,
            service_id: int,
            status_update: ServiceStatusUpdate,
            user: User,
            organization: Organization,
            background_tasks: BackgroundTasks
    ) -> Optional[ServiceResponse]:
        """Update service status and create history entry"""
        with get_db() as db:
            service = db.query(Service).filter(
                Service.service_id == service_id,
                Service.organization_id == organization.organization_id,
                Service.is_deleted == False,
            ).first()
            if not service:
                return None

            # Only update if status actually changed
            if service.current_status != status_update.status:
                old_status = service.current_status
                service.current_status = status_update.status

                # Create status history entry
                status_history = StatusHistory(
                    service_id=service.service_id,
                    organization_id=organization.organization_id,
                    status=status_update.status,
                    created_by_id=user.user_id
                )
                db.add(status_history)

                db.commit()
                db.refresh(service)

            # Broadcast real-time update
            background_tasks.add_task(
                broadcast,
                organization=organization,
                object=Object.SERVICE,
                event=Event.STATUS_UPDATED,
                data={
                    "service_id": str(service.service_id),
                    "name": service.name,
                    "old_status": old_status,
                    "new_status": status_update.status,
                    "message": status_update.message,
                    "updated_by": user.name,
                }
            )

            return ServiceResponse(
                service_id=service.service_id,
                name=service.name,
                description=service.description,
                current_status=service.current_status,
                created_at=service.created_at,
                updated_at=service.updated_at
            )

    def delete_service(self, service_id: int, user: User, organization: Organization,
                       background_tasks: BackgroundTasks) -> bool:
        """Delete service if user has access"""
        with get_db() as db:
            service = db.query(Service).filter(
                Service.service_id == service_id,
                Service.organization_id == organization.organization_id,
                Service.is_deleted == False,
            ).first()
            if not service:
                return False

            service.is_deleted = True
            service.updated_at = datetime.now()
            db.commit()

            # Broadcast real-time update
            background_tasks.add_task(
                broadcast,
                organization,
                object=Object.SERVICE,
                event=Event.DELETED,
                data={
                    "service_id": str(service_id),
                    "name": service.name,
                }
            )

        return True

    def get_service_uptime(
            self,
            service_id: int,
            user: User,
            organization: Organization,
            days: int = 30
    ) -> float:
        """Calculate service uptime percentage over specified days"""
        start_date = datetime.now() - timedelta(days=days)

        with get_db() as db:
            # Get all status changes in the period
            status_changes = db.query(StatusHistory).filter(
                StatusHistory.service_id == service_id,
                StatusHistory.organization_id == organization.organization_id,
                StatusHistory.created_at >= start_date,
                StatusHistory.is_deleted == False,
            ).order_by(StatusHistory.created_at).all()

            if not status_changes:
                # No status changes, assume operational
                return 100.0

            total_minutes = days * 24 * 60
            downtime_minutes = 0

            current_time = datetime.now()
            previous_time = start_date
            previous_status = ServiceStatus.OPERATIONAL

            for change in status_changes:
                # Calculate time in previous status
                duration = (change.created_at - previous_time).total_seconds() / 60

                if previous_status in [ServiceStatus.PARTIAL_OUTAGE, ServiceStatus.MAJOR_OUTAGE]:
                    downtime_minutes += duration
                elif previous_status == ServiceStatus.DEGRADED:
                    # Count degraded as 50% downtime
                    downtime_minutes += duration * 0.5

                previous_time = change.created_at
                previous_status = change.status

        # Account for time since last status change
        duration = (current_time - previous_time).total_seconds() / 60
        if previous_status in [ServiceStatus.PARTIAL_OUTAGE, ServiceStatus.MAJOR_OUTAGE]:
            downtime_minutes += duration
        elif previous_status == ServiceStatus.DEGRADED:
            downtime_minutes += duration * 0.5

        uptime_percentage = max(0, (total_minutes - downtime_minutes) / total_minutes * 100)

        return round(uptime_percentage, 2)

    def get_status_history_for_service(self, service_id: int, user: User, organization: Organization) -> List[
        StatusHistoryRead]:
        with get_db() as db:
            items = db.query(StatusHistory).filter(
                StatusHistory.service_id == service_id,
                StatusHistory.organization_id == organization.organization_id,
                StatusHistory.is_deleted == False,
            ).order_by(
                StatusHistory.created_at.desc()
            ).all()

            return [StatusHistoryRead.model_validate(item) for item in items]

    def create_status_history(self, status_data: StatusHistoryCreate, user: User,
                              organization: Organization) -> StatusHistory:
        with get_db() as db:
            status_entry = StatusHistory(
                service_id=status_data.service_id,
                organization_id=organization.organization_id,
                status=status_data.status,
                created_by_id=user.user_id,
            )
            db.add(status_entry)

            # Optionally update the current status on the service
            service = db.query(Service).filter(
                Service.service_id == status_data.service_id,
                Service.organization_id == organization.organization_id,
                Service.is_deleted == False,
            ).first()
            if service:
                service.current_status = status_data.status

            db.commit()
            db.refresh(status_entry)
            return status_entry
