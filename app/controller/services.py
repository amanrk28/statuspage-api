from fastapi import APIRouter, HTTPException, status, Query, Request, BackgroundTasks
from typing import List, Optional

from app.DTO.services import (
    ServiceResponse,
    ServiceWithHistoryResponse,
    ServiceCreate,
    ServiceUpdate,
    ServiceStatusUpdate
)
from app.DTO.status_history import StatusHistoryRead, StatusHistoryCreate
from app.services.services import ServiceCRUD

router = APIRouter(
    prefix="/services",
    tags=["services"],
    responses={404: {"description": "Not found"}},
)

service_crud = ServiceCRUD()


@router.get("/", response_model=List[ServiceWithHistoryResponse])
def get_services(request: Request):
    """Get services for the current user"""
    user = request.state.user
    organization = request.state.organization
    services = service_crud.get_services(
        user=user,
        organization=organization
    )

    return services


@router.post("/", response_model=Optional[ServiceResponse], status_code=status.HTTP_201_CREATED)
def create_service(request: Request, background_tasks: BackgroundTasks, service_in: ServiceCreate):
    """Create a new service"""

    user = request.state.user
    organization = request.state.organization
    try:
        service_response = service_crud.create_service(service_in=service_in, user=user, organization=organization,
                                                       background_tasks=background_tasks)
        return service_response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/{service_id}", response_model=ServiceWithHistoryResponse)
async def get_service(request: Request, background_tasks: BackgroundTasks, service_id: int):
    """Get service by ID with status history"""
    user = request.state.user
    organization = request.state.organization

    service = service_crud.get_service(service_id=service_id, user=user, organization=organization,
                                       background_tasks=background_tasks)

    return service


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
        request: Request,
        background_tasks: BackgroundTasks,
        service_id: int,
        service_in: ServiceUpdate,
):
    """Update service details"""
    user = request.state.user
    organization = request.state.organization

    service_response = service_crud.update_service(
        service_id=service_id,
        service_in=service_in,
        user=user,
        organization=organization,
        background_tasks=background_tasks
    )

    if not service_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return service_response


@router.put("/{service_id}/status", response_model=ServiceResponse)
async def update_service_status(
        request: Request,
        background_tasks: BackgroundTasks,
        service_id: int,
        status_update: ServiceStatusUpdate,
):
    """Update service status"""

    user = request.state.user
    organization = request.state.organization

    service_response = service_crud.update_service_status(
        service_id=service_id,
        status_update=status_update,
        user=user,
        organization=organization,
        background_tasks=background_tasks
    )

    if not service_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    return service_response


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(request: Request, background_tasks: BackgroundTasks, service_id: int):
    """Delete service"""
    user = request.state.user
    organization = request.state.organization

    success = service_crud.delete_service(service_id=service_id, user=user, organization=organization,
                                          background_tasks=background_tasks)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )


@router.get("/{service_id}/uptime", response_model=dict)
def get_service_uptime(
        request: Request,
        service_id: int,
        days: int = Query(30, ge=1, le=365),
):
    """Get service uptime percentage for specified period"""
    # Verify service access

    user = request.state.user
    organization = request.state.organization

    service = service_crud.get_service(service_id=service_id, user=user, organization=organization)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )

    uptime_percentage = service_crud.get_service_uptime(
        service_id=service_id,
        days=days,
        user=user,
        organization=organization
    )

    return {
        "service_id": service_id,
        "uptime_percentage": uptime_percentage,
        "period_days": days
    }


@router.get("/{service_id}/status-history", response_model=List[StatusHistoryRead])
def list_status_history(request: Request, service_id: int):
    user = request.state.user
    organization = request.state.organization
    return service_crud.get_status_history_for_service(service_id, user, organization)


@router.post("/status-history/", response_model=StatusHistoryRead)
def add_status_history(
        request: Request,
        status: StatusHistoryCreate,
):
    user = request.state.user
    organization = request.state.organization
    return service_crud.create_status_history(status, user, organization)
