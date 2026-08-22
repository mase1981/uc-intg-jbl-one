"""JBL soundbar select entities (EQ preset)."""

import logging
from typing import Any

from ucapi import StatusCodes, select
from ucapi_framework import SelectEntity

from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.const import STATE_ON, STATE_STANDBY
from uc_intg_jbl_one.device import JBLDevice

_LOG = logging.getLogger(__name__)


class JBLEQPresetSelect(SelectEntity):
    """EQ preset selector (JBL One 3.0+ firmware)."""

    def __init__(self, device_config: JBLConfig, device: JBLDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.eq_preset"
        super().__init__(
            entity_id,
            f"{device_config.name} EQ Preset",
            {
                select.Attributes.STATE: select.States.UNKNOWN,
                select.Attributes.OPTIONS: [],
                select.Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state not in (STATE_ON, STATE_STANDBY):
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update(
            {
                select.Attributes.STATE: select.States.ON,
                select.Attributes.OPTIONS: list(self._device.eq_preset_map.values()),
                select.Attributes.CURRENT_OPTION: self._device.eq_active_name,
            }
        )

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        if cmd_id == select.Commands.SELECT_OPTION:
            option = (params or {}).get("option", "")
            if await self._device.set_eq_preset(option):
                return StatusCodes.OK
            return StatusCodes.SERVER_ERROR
        return StatusCodes.NOT_IMPLEMENTED


def create_selects(device_config: JBLConfig, device: JBLDevice) -> list[SelectEntity]:
    if device.has_eq_presets:
        return [JBLEQPresetSelect(device_config, device)]
    return []
