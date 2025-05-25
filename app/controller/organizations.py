from fastapi import APIRouter, status, Request

from app.DTO.organization import OrganizationResponse, OrganizationCreate, OrganizationInvite
from app.core.auth import Auth0Manager
from app.db.models import Organization, User
from app.db.database import get_db
from app.utils.utils import slugify, get_username_from_email

router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
    responses={404: {"description": "Not found"}},
)

auth0_manager = Auth0Manager()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(request: Request, org_in: OrganizationCreate):
    """
    Create a new organization and add the current user as a member.
    This is the entry point for new users in the system.
    """
    await auth0_manager.initialize()
    org_name = slugify(org_in.org_name)
    display_name = org_in.org_name
    user_name = get_username_from_email(org_in.email_id)

    print("Creating organization {}".format(org_name))
    auth0_org = await auth0_manager.create_organization(
        org_name=org_name,
        org_display_name=display_name
    )
    print("Created organization {}".format(org_name))
    print("Creating user {}".format(user_name))

    auth0_user = await auth0_manager.create_user(email=org_in.email_id, password=org_in.password, name=user_name)

    print("Created user {}".format(user_name))
    print("Adding user {} to organization {}".format(user_name, org_in.org_name))

    await auth0_manager.add_user_to_organization(auth0_user.user_id, auth0_org.id)

    print("Added user {} to organization {}".format(user_name, org_in.org_name))

    with get_db() as db:
        # Create new organization
        organization = Organization(name=org_name, display_name=display_name, auth0_org_id=auth0_org.id)
        db.add(organization)
        db.commit()

        user = User(name=user_name, email=org_in.email_id, auth0_id=auth0_user.user_id,
                    organization_id=organization.organization_id)
        db.add(user)
        db.commit()

        organization_response = OrganizationResponse(name=organization.name, auth0_org_id=auth0_org.id)

    return organization_response

@router.post("/invite", status_code=status.HTTP_200_OK)
async def invite_user_to_organization(request: Request, invite_in: OrganizationInvite):
    organization = request.state.organization
    user = request.state.user

    await auth0_manager.initialize()

    print("Inviting the users to organization", organization.auth0_org_id)
    await auth0_manager.invite_user_to_organization(invite_in.email_id, user, organization)

