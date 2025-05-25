from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    auth0_org_id: str
    name: str

class OrganizationCreate(BaseModel):
    org_name: str
    email_id: str
    password: str


class OrganizationMetaData(BaseModel):
    created_via: str


class Auth0Organization(BaseModel):
    id: str
    display_name: str
    name: str
    metadata: OrganizationMetaData


class Auth0User(BaseModel):
    user_id: str
    email: str
    email_verified: bool
    name: str

class OrganizationInvite(BaseModel):
    email_id: str