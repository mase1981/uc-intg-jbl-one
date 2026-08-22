"""Configuration dataclass and manager for the JBL One integration."""

from dataclasses import dataclass

from ucapi_framework import BaseConfigManager


@dataclass
class JBLConfig:
    """Configuration for a single JBL soundbar."""

    identifier: str = ""
    name: str = ""
    host: str = ""
    uuid: str = ""  # Stable device id from getDeviceInfo (survives IP changes)
    mac: str = ""
    model: str = ""


class JBLConfigManager(BaseConfigManager[JBLConfig]):
    """Config manager bound to :class:`JBLConfig`."""
