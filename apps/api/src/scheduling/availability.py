from datetime import datetime


class AvailabilityService:
    def is_available(self, resource_id: str, start: datetime, end: datetime) -> bool:
        return True
