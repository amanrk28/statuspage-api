from .config import Environment
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.controller import organizations, services, incident, public
from app.db import Organization
from app.db.database import Base, engine, get_db
from app.config import settings
from app.middleware.auth_middleware import AuthMiddleware
from app.websocket.manager import manager

app = FastAPI()
# Middlewares
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(organizations.router, prefix="/api")
app.include_router(services.router, prefix="/api")
app.include_router(incident.router, prefix="/api")
app.include_router(public.router, prefix="/api")


@app.get("/api/healthcheck")
async def health():
    print("Healthcheck")
    if settings.CREATE_TABLES and settings.ENVIRONMENT == Environment.LOCAL:
        print("Creating tables")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    return {"message": "Healthcheck success!"}


@app.websocket("/ws/{org_info}")
async def websocket_endpoint(websocket: WebSocket, org_info: str):
    org_id = org_info.strip()
    # If socket is subscribed from public page, then org slug will be sent
    if "org_" not in org_info:
        with get_db() as db:
            org = db.query(Organization).filter(Organization.name == org_info).first()
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            org_id = org.auth0_org_id

    await manager.connect(websocket, org_id)
    try:
        while True:
            await websocket.receive_text()  # Keeps connection open
    except Exception:
        pass
    finally:
        manager.disconnect(websocket, org_id)
