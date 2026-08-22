"""JBL soundbar remote entity - full button surface for activities."""

import logging
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import (
    Buttons,
    Size,
    UiPage,
    create_btn_mapping,
    create_ui_icon,
    create_ui_text,
)
from ucapi_framework import RemoteEntity

from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.const import (
    KEY_ATMOS,
    KEY_BASS_BOOST,
    KEY_CALIBRATION,
    KEY_MOMENT,
    KEY_MUTE,
    KEY_PLAY_PAUSE,
    KEY_REAR,
    KEY_SOURCE_BLUETOOTH,
    KEY_SOURCE_HDMI,
    KEY_SOURCE_TV,
    KEY_VOLUME_DOWN,
    KEY_VOLUME_UP,
    STATE_ON,
    STATE_STANDBY,
)
from uc_intg_jbl_one.device import JBLDevice

_LOG = logging.getLogger(__name__)

# Simple command name -> sendAppController key.
COMMAND_MAP: dict[str, str] = {
    "VOLUME_UP": KEY_VOLUME_UP,
    "VOLUME_DOWN": KEY_VOLUME_DOWN,
    "MUTE": KEY_MUTE,
    "PLAY_PAUSE": KEY_PLAY_PAUSE,
    "MOMENT": KEY_MOMENT,
    "CALIBRATION": KEY_CALIBRATION,
    "REAR": KEY_REAR,
    "BASS_BOOST": KEY_BASS_BOOST,
    "ATMOS": KEY_ATMOS,
    "SOURCE_HDMI": KEY_SOURCE_HDMI,
    "SOURCE_TV": KEY_SOURCE_TV,
    "SOURCE_BLUETOOTH": KEY_SOURCE_BLUETOOTH,
    "SMART_MODE": "surround",
}

SIMPLE_COMMANDS = (
    ["POWER", "POWER_ON", "POWER_OFF"]
    + list(COMMAND_MAP.keys())
    + ["NIGHT_MODE_ON", "NIGHT_MODE_OFF", "PURE_VOICE_ON", "PURE_VOICE_OFF"]
)


class JBLRemote(RemoteEntity):
    """Exposes the full JBL button surface as simple commands for activities."""

    def __init__(self, device_config: JBLConfig, device: JBLDevice) -> None:
        self._device = device
        entity_id = f"remote.{device_config.identifier}"
        super().__init__(
            entity_id,
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=SIMPLE_COMMANDS,
            button_mapping=[
                create_btn_mapping(Buttons.POWER, short="POWER"),
                create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
                create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
                create_btn_mapping(Buttons.MUTE, short="MUTE"),
                create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.DPAD_MIDDLE, short="MOMENT"),
                create_btn_mapping(Buttons.HOME, short="SOURCE_HDMI"),
            ],
            ui_pages=[
                UiPage("main", "JBL", grid=Size(4, 6), items=[
                    create_ui_icon("uc:power-on", 0, 0, cmd="POWER_ON"),
                    create_ui_icon("uc:power-off", 3, 0, cmd="POWER_OFF"),
                    create_ui_icon("uc:volume-up", 3, 2, cmd="VOLUME_UP"),
                    create_ui_icon("uc:volume-down", 3, 3, cmd="VOLUME_DOWN"),
                    create_ui_icon("uc:mute", 3, 4, cmd="MUTE"),
                    create_ui_icon("uc:play", 1, 0, cmd="PLAY_PAUSE"),
                    create_ui_text("Moment", 1, 2, cmd="MOMENT"),
                    create_ui_text("Calibrate", 2, 2, cmd="CALIBRATION"),
                    create_ui_text("Smart Mode", 0, 3, cmd="SMART_MODE"),
                    create_ui_text("Bass", 1, 3, cmd="BASS_BOOST"),
                    create_ui_text("Atmos", 2, 3, cmd="ATMOS"),
                    create_ui_text("Rear", 0, 4, cmd="REAR"),
                ]),
                UiPage("sources", "Sources", grid=Size(4, 6), items=[
                    create_ui_text("HDMI", 0, 0, cmd="SOURCE_HDMI"),
                    create_ui_text("TV", 1, 0, cmd="SOURCE_TV"),
                    create_ui_text("Bluetooth", 2, 0, cmd="SOURCE_BLUETOOTH"),
                    create_ui_text("Night On", 0, 2, cmd="NIGHT_MODE_ON"),
                    create_ui_text("Night Off", 1, 2, cmd="NIGHT_MODE_OFF"),
                    create_ui_text("Voice On", 0, 3, cmd="PURE_VOICE_ON"),
                    create_ui_text("Voice Off", 1, 3, cmd="PURE_VOICE_OFF"),
                ]),
            ],
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        state = remote.States.ON if self._device.state in (STATE_ON, STATE_STANDBY) else remote.States.UNAVAILABLE
        self.update({remote.Attributes.STATE: state})

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == remote.Commands.ON:
                await self._device.power_on()
                return StatusCodes.OK
            if cmd_id == remote.Commands.OFF:
                await self._device.power_off()
                return StatusCodes.OK
            if cmd_id == remote.Commands.TOGGLE:
                await self._device.power_toggle()
                return StatusCodes.OK
            if cmd_id != remote.Commands.SEND_CMD:
                return StatusCodes.NOT_IMPLEMENTED
            return await self._run((params or {}).get("command", ""))
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Remote command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _run(self, command: str) -> StatusCodes:
        if command == "POWER":
            await self._device.power_toggle()
            return StatusCodes.OK
        if command == "POWER_ON":
            await self._device.power_on()
            return StatusCodes.OK
        if command == "POWER_OFF":
            await self._device.power_off()
            return StatusCodes.OK
        if command == "SMART_MODE":
            await self._device.set_smart_mode(not self._device.smart_mode)
            return StatusCodes.OK
        if command == "NIGHT_MODE_ON":
            await self._device.set_night_mode(True)
            return StatusCodes.OK
        if command == "NIGHT_MODE_OFF":
            await self._device.set_night_mode(False)
            return StatusCodes.OK
        if command == "PURE_VOICE_ON":
            await self._device.set_pure_voice(True)
            return StatusCodes.OK
        if command == "PURE_VOICE_OFF":
            await self._device.set_pure_voice(False)
            return StatusCodes.OK
        key = COMMAND_MAP.get(command)
        if key is None:
            return StatusCodes.NOT_IMPLEMENTED
        await self._device.send_raw_key(key)
        return StatusCodes.OK


def create_remote(device_config: JBLConfig, device: JBLDevice) -> list[JBLRemote]:
    return [JBLRemote(device_config, device)]
