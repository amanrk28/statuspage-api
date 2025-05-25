from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import List
from fastapi.params import Query

from app.DTO.incident import IncidentRead, IncidentCreate, IncidentResponse, IncidentUpdateRequest, IncidentUpdateRead, \
    IncidentUpdateCreate
from app.services.incident import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"], responses={404: {"description": "Not found"}}, )

incident_crud = IncidentService()


@router.post("/", response_model=IncidentRead)
async def create_incident(request: Request, background_tasks: BackgroundTasks, data: IncidentCreate):
    user = request.state.user
    organization = request.state.organization
    return incident_crud.create_incident(data, user, organization, background_tasks)


@router.get("/", response_model=List[IncidentRead])
def list_incidents(request: Request, resolved: str = Query(default="none")):
    user = request.state.user
    organization = request.state.organization
    return incident_crud.get_all_incidents(resolved, user, organization)


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(request: Request, incident_id: int):
    user = request.state.user
    organization = request.state.organization
    incident = incident_crud.get_incident(incident_id, user, organization)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.put("/{incident_id}", response_model=IncidentRead)
async def update_incident(request: Request, background_tasks: BackgroundTasks, incident_id: int,
                          updates: IncidentUpdateRequest):
    user = request.state.user
    organization = request.state.organization
    incident = incident_crud.update_incident(incident_id, updates, user, organization, background_tasks)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.delete("/{incident_id}")
def delete_incident(request: Request, background_tasks: BackgroundTasks, incident_id: int):
    user = request.state.user
    organization = request.state.organization
    incident = incident_crud.delete_incident(incident_id, user, organization, background_tasks)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"detail": "Incident deleted"}


# Incident Updates
@router.post("/updates", response_model=IncidentUpdateRead)
def create_update(request: Request, background_tasks: BackgroundTasks, data: IncidentUpdateCreate):
    user = request.state.user
    organization = request.state.organization
    return incident_crud.create_incident_update(data, user, organization, background_tasks)


@router.get("/{incident_id}/updates", response_model=List[IncidentUpdateRead])
def get_updates(request: Request, incident_id: int):
    user = request.state.user
    organization = request.state.organization
    return incident_crud.get_incident_updates(incident_id, user, organization)
