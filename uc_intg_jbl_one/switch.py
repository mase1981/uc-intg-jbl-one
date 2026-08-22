"""JBL soundbar switch entities (night mode, smart mode, pure voice)."""

import logging
from typing import Any, Callable, Coroutine

from ucapi import StatusCodes, switch
from ucapi_framework import SwitchEntity

from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.const import STATE_ON, STATE_STANDBY
from uc_intg_jbl_one.device import JBLDevice

_LOG = logging.getLogger(__name__)


class _JBLModeSwitch(SwitchEntity):
    """A soundbar mode toggle backed by a device getter/setter."""

    def __init__(
        self,
        device_config: JBLConfig,
        device: JBLDevice,
        sub_id: str,
        label: str,
        getter: Callable[[JBLDevice], bool],
        setter: Callable[[JBLDevice, bool], Coroutine[Any, Any, None]],
    ) -> None:
        self._device = device
        self._getter = getter
        self._setter = setter
        entity_id = f"switch.{device_config.identifier}.{sub_id}"
        super().__init__(
            entity_id,
            f"{device_config.name} {label}",
            [switch.Features.ON_OFF, switch.Features.TOGGLE],
            {switch.Attributes.STATE: switch.States.UNKNOWN},
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state not in (STATE_ON, STATE_STANDBY):
            self.update({switch.Attributes.STATE: switch.States.UNAVAILABLE})
            return
        self.update(
            {switch.Attributes.STATE: switch.States.ON if self._getter(self._device) else switch.States.OFF}
        )

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == switch.Commands.ON:
                await self._setter(self._device, True)
            elif cmd_id == switch.Commands.OFF:
                await self._setter(self._device, False)
            elif cmd_id == switch.Commands.TOGGLE:
                await self._setter(self._device, not self._getter(self._device))
            else:
                return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Switch command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def create_switches(device_config: JBLConfig, device: JBLDevice) -> list[SwitchEntity]:
    entities: list[SwitchEntity] = []
    if device.has_night_mode:
        entities.append(
            _JBLModeSwitch(
                device_config, device, "night_mode", "Night Mode",
                lambda d: d.night_mode, JBLDevice.set_night_mode,
            )
        )
    if device.has_smart_mode:
        entities.append(
            _JBLModeSwitch(
                device_config, device, "smart_mode", "Smart Mode",
                lambda d: d.smart_mode, JBLDevice.set_smart_mode,
            )
        )
    if device.has_pure_voice:
        entities.append(
            _JBLModeSwitch(
                device_config, device, "pure_voice", "Pure Voice",
                lambda d: d.pure_voice, JBLDevice.set_pure_voice,
            )
        )
    return entities
