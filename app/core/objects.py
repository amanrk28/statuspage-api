import enum


class Event(enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_UPDATED = "status_updated"
    BULK_UPDATED = "bulk_updated"

class Object(enum.Enum):
    SERVICE = "service"
    INCIDENT = "incident"
    INCIDENT_UPDATE = "incident_update"
    STATUS = "status"