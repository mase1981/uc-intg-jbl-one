"""Integration driver for JBL One soundbars."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.device import JBLDevice
from uc_intg_jbl_one.media_player import create_media_player
from uc_intg_jbl_one.remote import create_remote
from uc_intg_jbl_one.select import create_selects
from uc_intg_jbl_one.sensor import create_sensors
from uc_intg_jbl_one.switch import create_switches


class JBLDriver(BaseIntegrationDriver[JBLDevice, JBLConfig]):
    """Builds the entity set for each JBL soundbar based on its capabilities."""

    def __init__(self) -> None:
        super().__init__(
            device_class=JBLDevice,
            entity_classes=[
                create_media_player,
                create_remote,
                create_switches,
                create_selects,
                create_sensors,
            ],
            driver_id="uc_intg_jbl_one",
            require_connection_before_registry=True,
        )
