from enum import Enum
from .settings import get_settings

class ServiceMode(str, Enum):
    MOCK = "mock"
    OFFLINE = "offline"
    ONLINE = "online"

def current_mode() -> ServiceMode:
    mode = get_settings().flags.service_mode.lower().strip()
    if mode == "mock":
        return ServiceMode.MOCK
    if mode == "online":
        return ServiceMode.ONLINE
    return ServiceMode.OFFLINE