from fastapi import HTTPException
from app.config import settings
from app.DTO.organization import Auth0Organization, Auth0User
from app.db.models import User, Organization
import httpx

class Auth0Manager:
    def __init__(self):
        self.domain = settings.AUTH0_DOMAIN
        self.client_id = settings.AUTH0_CLIENT_ID
        self.client_secret = settings.AUTH0_CLIENT_SECRET
        self.api_audience = settings.AUTH0_AUDIENCE
        self.token = None

    async def initialize(self):
        """Call this after creating the instance"""
        self.token = await self.get_management_token()
        return self

    async def get_management_token(self) -> str:
        """Get Management API access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{settings.AUTH0_DOMAIN}/oauth/token",
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "audience": self.api_audience,
                        "grant_type": "client_credentials"
                    }
                )
                return response.json()["access_token"]
        except Exception as e:
            print(e)
            return ""

    async def create_organization(self, org_name: str, org_display_name: str) -> Auth0Organization:
        token = self.token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/organizations",
                headers={"Authorization": f"Bearer {token}", 'Content-Type': 'application/json'},
                json={
                    "name": org_name,
                    "display_name": org_display_name,
                    "metadata": {
                        "created_via": "fastAPI"
                    },
                    "enabled_connections": [
                        {
                            "connection_id": "con_YSVwsH8TW8qkt1Q2",
                            "assign_membership_on_login": True,
                            "show_as_button": True,
                            "is_signup_enabled": True
                        }
                    ]
                },
            )
            res = response.json()
            if response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=res.get("message"))
            print("Organization created", response.status_code, response.json())
            return Auth0Organization(**res)

    async def create_user(self, email: str, password: str, name: str) -> Auth0User:
        token = self.token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/users",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "email": email,
                    "password": password,
                    "name": name,
                    "nickname": name.lower(),
                    "connection": "Username-Password-Authentication"
                },
            )
            res = response.json()
            if response.status_code != 201:
                raise HTTPException(status_code=response.status_code, detail=res.get("message"))
            print("User created", response.status_code, response.json())
            return Auth0User(**response.json())

    async def add_user_to_organization(self, user_id: str, org_id: str):
        """Add user to organization with optional roles"""
        token = self.token

        async with httpx.AsyncClient() as client:
            # Add user to organization
            response = await client.post(
                f"https://{self.domain}/api/v2/organizations/{org_id}/members",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "members": [user_id],
                }
            )
            if response.status_code != 204:
                res = response.json()
                raise HTTPException(status_code=response.status_code, detail=res.get("message"))

            response = await client.post(
                f"https://{self.domain}/api/v2/organizations/{org_id}/members/{user_id}/roles",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"roles": ["rol_0SNxlWyrpyXzGncw"]}
            )
            if response.status_code != 204:
                res = response.json()
                raise HTTPException(status_code=response.status_code, detail=res.get("message"))

    async def invite_user_to_organization(self, email_id: str, user: User, organization: Organization):
        """Invite user to organization with optional roles"""
        token = self.token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{self.domain}/api/v2/organizations/{organization.auth0_org_id}/invitations",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", 'Accept': 'application/json'},
                json={
                    "inviter": {
                        "name": user.name,
                    },
                    "invitee": {
                        "email": email_id,
                    },
                    "client_id": settings.AUTH0_CLIENT_AUDIENCE,
                    "send_invitation_email": True,
                }
            )
            if response.status_code != 200:
                res = response.json()
                raise HTTPException(status_code=response.status_code, detail=res.get("message"))
