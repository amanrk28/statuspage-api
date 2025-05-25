import datetime

from app.core.objects import Object, Event
from app.db import Organization
from app.websocket.manager import manager


async def broadcast(organization: Organization, object: Object, event: Event, data: dict, **kwargs):
    print(f"\n--- Preparing broadcast for {object} {event} ---")

    socket_data = {
        "object": object.value,
        "event": event.value,
        "org_id": organization.auth0_org_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "payload": {
            **data,  # Include the core data (e.g., service_id, name)
            **kwargs  # Include any additional keyword arguments
        }
    }

    print(f"Constructed Socket Data: {socket_data}")

    await manager.broadcast_to_organization(str(organization.auth0_org_id), socket_data)
