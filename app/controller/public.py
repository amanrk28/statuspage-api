from fastapi import APIRouter,Request

from app.services.public import PublicStatusCRUD
from app.DTO.public import PublicStatus

router = APIRouter(
    prefix="/public",
    tags=["public"],
    responses={404: {"description": "Not found"}},
)

public_status = PublicStatusCRUD()

@router.get("/{org_slug}", response_model=PublicStatus)
async def get_public_services(org_slug: str):
    response = public_status.get_status(org_slug=org_slug)
    return response
