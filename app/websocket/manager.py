from typing import List, Dict, Any
from fastapi import WebSocket
import json

class ConnectionManager:
    def __init__(self):
        # Dictionary to store active connections, grouped by auth0_org_id
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, auth0_org_id: str):
        await websocket.accept()
        if auth0_org_id not in self.active_connections:
            self.active_connections[auth0_org_id] = []
        self.active_connections[auth0_org_id].append(websocket)
        print(
            f"WebSocket connected for organization {auth0_org_id}. Total connections: {len(self.active_connections[auth0_org_id])}")

    def disconnect(self, websocket: WebSocket, auth0_org_id: str):
        if auth0_org_id in self.active_connections:
            try:
                self.active_connections[auth0_org_id].remove(websocket)
                if not self.active_connections[auth0_org_id]:
                    del self.active_connections[auth0_org_id]  # Clean up empty list
            except ValueError:
                # WebSocket might have already been removed or not found
                pass
        print(f"WebSocket disconnected for organization {auth0_org_id}.")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_organization(self, auth0_org_id: str, message: Dict[str, Any]):
        if auth0_org_id in self.active_connections:
            # Convert dictionary message to JSON string
            json_message = json.dumps(message)
            disconnected_sockets = []
            for connection in self.active_connections[auth0_org_id]:
                try:
                    await connection.send_text(json_message)
                except RuntimeError as e:
                    # Handle cases where the connection might be closed unexpectedly
                    print(f"Error sending to WebSocket for org {auth0_org_id}: {e}")
                    disconnected_sockets.append(connection)
                except Exception as e:
                    print(f"Unexpected error sending to WebSocket for org {auth0_org_id}: {e}")
                    disconnected_sockets.append(connection)
            # Remove disconnected sockets
            for ws in disconnected_sockets:
                self.active_connections[auth0_org_id].remove(ws)
            if not self.active_connections[auth0_org_id]:
                del self.active_connections[auth0_org_id]
        else:
            print(f"No active WebSockets for organization {auth0_org_id}.")


manager = ConnectionManager()
