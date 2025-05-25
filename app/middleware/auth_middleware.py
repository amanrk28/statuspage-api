from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.orm import Session
from app.db.database import get_db_session
import httpx
import time
from typing import Dict, Any

from app.config import settings
from app.db.models import User, Organization

jwks_cache: Dict[str, Any] = {}
JWKS_CACHE_TTL_SECONDS = 3600


async def get_jwks():
    global jwks_cache
    if not jwks_cache or (jwks_cache and (jwks_cache.get("timestamp", 0) + JWKS_CACHE_TTL_SECONDS) < int(time.time())):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json")
            response.raise_for_status()
            jwks_cache = response.json()
    return jwks_cache


async def verify_token(token: str) -> dict:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")

    jwks = await get_jwks()

    key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)

    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth credentials")
    try:
        payload = jwt.decode(
            token,
            key,
            audience=settings.AUTH0_CLIENT_AUDIENCE,
            algorithms=settings.AUTH0_ALGORITHMS,
            issuer=f"https://{settings.AUTH0_DOMAIN}/"
        )
        return payload
    except JWTError as e:
        print("JWT error", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")
    except Exception as e:  # Catch any other unexpected errors during decode
        print("error", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Token verification error: {e}")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(
                "/api/public") or request.url.path == '/api/healthcheck' or request.url.path == '/api/organizations':
            return await call_next(request)

        # Dependency injection doesn't work in middleware directly
        db: Session = get_db_session()
        try:
            user = db.query(User).first()
            organization = db.query(Organization).first()

            request.state.user = user
            request.state.organization = organization
        finally:
            db.close()

        # return await call_next(request)

        auth_header = request.headers.get("Authorization")
        auth0_org_id = request.headers.get("x-tenant-id")
        auth0_user_id = request.headers.get("x-user-id")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

        token = auth_header.split(" ")[1]
        claims = None

        try:
            claims = await verify_token(token)
            request.state.claims = claims
        except Exception as e:
            if not auth0_org_id and not auth0_user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
            else:
                claims = {
                    "org_id": auth0_org_id,
                    "sub": auth0_user_id,
                }

        # Pass claims to the request state so downstream routes/handlers can access them
        if request.url.path.startswith("/api/auth") and request.method == 'POST':
            # Passing claims only to this API in order to create an organization
            request.state.claims = claims
            return await call_next(request)

        db: Session = get_db_session()
        try:
            user, organization = sync_user_and_org_from_claims(claims, db)
            request.state.user = user
            request.state.organization = organization
        finally:
            db.close()

        return await call_next(request)


def sync_user_and_org_from_claims(claims: dict, db: Session):
    auth0_user_id = claims.get("sub")
    auth0_org_id = claims.get("org_id")

    if not auth0_user_id:
        raise ValueError("No user ID found in token")

    if not auth0_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Organization ID (org_id) missing from token. Access denied in multi-tenant context.")

    user = db.query(User).filter(User.auth0_id == auth0_user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    organization = db.query(Organization).filter(Organization.auth0_org_id == auth0_org_id,
                                                 Organization.is_deleted == False).first()
    if not organization:
        # This scenario implies a mismatch.
        # You might create the organization here if it's a new Auth0 org,
        # but typically you pre-create Auth0 orgs and sync their IDs.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Organization not found in internal database. Contact administrator.")

    return user, organization
