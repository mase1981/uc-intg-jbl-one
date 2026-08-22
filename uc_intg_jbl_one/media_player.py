"""JBL soundbar media_player entity."""

import logging
from typing import Any

from ucapi import StatusCodes, media_player
from ucapi_framework import MediaPlayerEntity

from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.const import STATE_ON, STATE_STANDBY
from uc_intg_jbl_one.device import JBLDevice

_LOG = logging.getLogger(__name__)

FEATURES = [
    media_player.Features.ON_OFF,
    media_player.Features.TOGGLE,
    media_player.Features.VOLUME,
    media_player.Features.VOLUME_UP_DOWN,
    media_player.Features.MUTE_TOGGLE,
    media_player.Features.PLAY_PAUSE,
    media_player.Features.MEDIA_TITLE,
    media_player.Features.SELECT_SOURCE,
]


class JBLMediaPlayer(MediaPlayerEntity):
    """Media player for a JBL One soundbar."""

    def __init__(self, device_config: JBLConfig, device: JBLDevice) -> None:
        self._device = device
        entity_id = f"media_player.{device_config.identifier}"
        super().__init__(
            entity_id,
            device_config.name,
            FEATURES,
            {
                media_player.Attributes.STATE: media_player.States.UNKNOWN,
                media_player.Attributes.VOLUME: 0,
                media_player.Attributes.MUTED: False,
                media_player.Attributes.SOURCE: "",
                media_player.Attributes.SOURCE_LIST: [],
                media_player.Attributes.MEDIA_TITLE: "",
            },
            device_class=media_player.DeviceClasses.SPEAKER,
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if self._device.state not in (STATE_ON, STATE_STANDBY):
            self.update({media_player.Attributes.STATE: media_player.States.UNAVAILABLE})
            return
        if self._device.state == STATE_STANDBY:
            state = media_player.States.OFF
        elif self._device.transport_state == "PLAYING":
            state = media_player.States.PLAYING
        elif self._device.transport_state in ("PAUSED_PLAYBACK", "PAUSED"):
            state = media_player.States.PAUSED
        else:
            state = media_player.States.ON
        self.update(
            {
                media_player.Attributes.STATE: state,
                media_player.Attributes.VOLUME: self._device.volume,
                media_player.Attributes.MUTED: self._device.muted,
                media_player.Attributes.SOURCE: self._device.source,
                media_player.Attributes.SOURCE_LIST: self._device.source_list,
                media_player.Attributes.MEDIA_TITLE: self._device.track,
            }
        )

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            match cmd_id:
                case media_player.Commands.ON:
                    await self._device.power_on()
                case media_player.Commands.OFF:
                    await self._device.power_off()
                case media_player.Commands.TOGGLE:
                    await self._device.power_toggle()
                case media_player.Commands.PLAY_PAUSE:
                    await self._device.send_raw_key("musicPlayPause")
                case media_player.Commands.VOLUME:
                    await self._device.set_volume(int((params or {}).get("volume", 0)))
                case media_player.Commands.VOLUME_UP:
                    await self._device.send_raw_key("volumeUp")
                case media_player.Commands.VOLUME_DOWN:
                    await self._device.send_raw_key("volumeDown")
                case media_player.Commands.MUTE_TOGGLE:
                    await self._device.send_raw_key("mute")
                case media_player.Commands.SELECT_SOURCE:
                    await self._device.select_source((params or {}).get("source", ""))
                case _:
                    return StatusCodes.NOT_IMPLEMENTED
            return StatusCodes.OK
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR


def create_media_player(device_config: JBLConfig, device: JBLDevice) -> list[JBLMediaPlayer]:
    return [JBLMediaPlayer(device_config, device)]
