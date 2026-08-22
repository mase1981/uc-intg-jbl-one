"""JBL soundbar device - polls one soundbar over httpapi + UPnP.

The soundbar stays reachable on the network even in standby, so power state is
inferred from the playback medium (``play_medium == "UNKNOWN"`` -> standby). If
the device becomes unreachable (unplugged / IP changed) the poll raises and the
framework's watchdog reconnects; on reconnect we first try to re-resolve the IP
by the device's stable mDNS uuid (upstream issue #30).
"""

import asyncio
import logging
from typing import Any

import aiohttp
from ucapi_framework import DeviceEvents, PollingDevice

from uc_intg_jbl_one import discovery
from uc_intg_jbl_one.client import JBLClient
from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.const import (
    KEY_POWER,
    KEY_SMART_MODE,
    MAX_ATTR_LEN,
    PLAY_MEDIUM_SOURCE_MAP,
    SOURCE_BLUETOOTH,
    SOURCE_HDMI,
    SOURCE_KEYS,
    SOURCE_TV,
    STATE_ON,
    STATE_STANDBY,
    STATE_UNAVAILABLE,
)

_LOG = logging.getLogger(__name__)

SOURCE_LIST = [SOURCE_HDMI, SOURCE_TV, SOURCE_BLUETOOTH]


class JBLDevice(PollingDevice):
    """One JBL One soundbar."""

    def __init__(self, device_config: JBLConfig, **kwargs: Any) -> None:
        super().__init__(device_config, poll_interval=10, **kwargs)
        self._device_config = device_config
        self._client: JBLClient | None = None
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._state: str = STATE_UNAVAILABLE

        # Playback / media state.
        self.volume: int = 0
        self.muted: bool = False
        self.play_medium: str = "UNKNOWN"
        self.transport_state: str = ""
        self.track: str = ""

        # Mode state.
        self.night_mode: bool = False
        self.smart_mode: bool = False
        self.pure_voice: bool = False

        # EQ presets.
        self.eq_preset_map: dict[str, str] = {}
        self.eq_preset_data: dict[str, dict[str, Any]] = {}
        self.eq_active_name: str = ""

        # Rear speakers.
        self.rears: list[dict[str, Any]] = []

        # Capabilities (populated on connect).
        self.model: str = device_config.model or ""
        self.firmware: str = ""
        self.has_night_mode: bool = False
        self.has_smart_mode: bool = False
        self.has_pure_voice: bool = False
        self.has_eq_presets: bool = False

    # -- identity ------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def state(self) -> str:
        return self._state

    @property
    def source(self) -> str:
        return PLAY_MEDIUM_SOURCE_MAP.get((self.play_medium or "").upper(), "")

    @property
    def source_list(self) -> list[str]:
        return SOURCE_LIST

    @property
    def rear_count(self) -> int:
        return len(self.rears)

    @property
    def is_authentics(self) -> bool:
        return "authentics" in (self.model or "").lower()

    # -- connection lifecycle ------------------------------------------
    async def establish_connection(self) -> JBLClient:
        async with self._connect_lock:
            if self._client is None:
                self._client = JBLClient(self._device_config.host)
            await self._client.connect()

        device_type = await self._client.get_device_type()
        model = device_type.get("hm_product_name", "") if device_type else ""
        if not model or model == "unknown_product":
            # Device may have changed IP - try to re-resolve by uuid (issue #30).
            if await self._reresolve_host():
                device_type = await self._client.get_device_type()
                model = device_type.get("hm_product_name", "") if device_type else ""
            if not model or model == "unknown_product":
                raise ConnectionError(f"Cannot reach JBL soundbar at {self.address}")

        self.model = model
        if model and model != self._device_config.model:
            self.update_config(model=model)

        try:
            info = await self._client.get_device_info()
            self.firmware = info.get("firmware", "") if info else ""
            await self._update_state()
        except (aiohttp.ClientError, ConnectionError) as err:
            _LOG.warning("[%s] Initial state query failed, using defaults: %s", self.log_id, err)

        return self._client

    async def _reresolve_host(self) -> bool:
        new_host = await discovery.resolve_host_by_uuid(self._device_config.uuid)
        if new_host and new_host != self._device_config.host:
            _LOG.info("[%s] Soundbar moved to %s - updating", self.log_id, new_host)
            self.update_config(host=new_host)
            self._device_config.host = new_host
            async with self._connect_lock:
                if self._client is not None:
                    await self._client.close()
                self._client = JBLClient(new_host)
                await self._client.connect()
            return True
        return False

    async def poll_device(self) -> None:
        if self._client is None:
            return
        try:
            await self._update_state()
            self.push_update()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.debug("[%s] Poll error: %s", self.log_id, err)
            if self._state != STATE_UNAVAILABLE:
                self._state = STATE_UNAVAILABLE
                self.events.emit(DeviceEvents.DISCONNECTED, self.identifier)

    async def _update_state(self) -> None:
        assert self._client is not None
        playback = await self._client.get_playback_info()
        if not playback:
            raise ConnectionError("Failed to get playback status")

        self.play_medium = playback.get("play_medium", "UNKNOWN") or "UNKNOWN"
        self.transport_state = playback.get("transport_state", "") or ""
        self.track = (playback.get("track", "") or "")[:MAX_ATTR_LEN]
        try:
            self.volume = int(playback.get("volume_level") or 0)
        except (ValueError, TypeError):
            self.volume = 0
        self.muted = str(playback.get("mute", "0")) == "1"

        night = await self._client.get_night_mode()
        if night is not None:
            self.has_night_mode = True
            self.night_mode = night == "on"

        smart = await self._client.get_smart_mode()
        if smart is not None:
            self.has_smart_mode = True
            self.smart_mode = smart == "on"

        pure = await self._client.get_pure_voice()
        if pure is not None:
            self.has_pure_voice = True
            self.pure_voice = pure == "on"

        rears = await self._client.get_rear_speakers()
        self.rears = [r for r in rears if isinstance(r, dict) and r.get("capicity") is not None]

        presets = await self._client.get_eq_presets()
        if presets:
            self.has_eq_presets = True
            self.eq_preset_map = presets["preset_map"]
            self.eq_preset_data = presets["preset_data"]
            self.eq_active_name = presets.get("active_name") or ""

        self._state = STATE_ON if self.play_medium != "UNKNOWN" else STATE_STANDBY

    async def disconnect(self) -> None:
        async with self._connect_lock:
            if self._client is not None:
                await self._client.close()
                self._client = None
        self._state = STATE_UNAVAILABLE
        await super().disconnect()

    # -- commands ------------------------------------------------------
    async def _send_key(self, key: str) -> bool:
        """Send a key press, reconnecting once on a dropped connection (#25)."""
        for attempt in range(2):
            if self._client is None:
                self._client = JBLClient(self._device_config.host)
                await self._client.connect()
            try:
                return await self._client.send_key(key)
            except (aiohttp.ClientError, ConnectionResetError, OSError) as err:
                _LOG.debug("[%s] send_key(%s) attempt %d failed: %s", self.log_id, key, attempt + 1, err)
                await self._client.close()
                self._client = None
        _LOG.warning("[%s] Failed to send key %s", self.log_id, key)
        return False

    async def power_on(self) -> None:
        if self._state != STATE_ON:
            await self._send_key(KEY_POWER)
        self._state = STATE_ON
        self.push_update()

    async def power_off(self) -> None:
        if self.is_authentics:
            # Authentics models cannot be powered back on remotely (issue #43).
            _LOG.warning("[%s] Power-off suppressed for Authentics model (cannot power on remotely)", self.log_id)
            return
        await self._send_key(KEY_POWER)
        self._state = STATE_STANDBY
        self.push_update()

    async def power_toggle(self) -> None:
        await self._send_key(KEY_POWER)
        self.push_update()

    async def set_volume(self, value: int) -> None:
        value = max(0, min(100, int(value)))
        if self._client is None:
            self._client = JBLClient(self._device_config.host)
            await self._client.connect()
        try:
            await self._client.set_volume(value)
            self.volume = value
            self.push_update()
        except (aiohttp.ClientError, OSError) as err:
            _LOG.warning("[%s] set_volume failed: %s", self.log_id, err)

    async def send_raw_key(self, key: str) -> bool:
        return await self._send_key(key)

    async def select_source(self, source: str) -> bool:
        key = SOURCE_KEYS.get(source)
        if key is None:
            _LOG.warning("[%s] Unknown source: %s", self.log_id, source)
            return False
        return await self._send_key(key)

    async def set_night_mode(self, enabled: bool) -> None:
        if self._client is None:
            self._client = JBLClient(self._device_config.host)
            await self._client.connect()
        await self._client.set_night_mode(enabled)
        self.night_mode = enabled
        self.push_update()

    async def set_smart_mode(self, enabled: bool) -> None:
        # Smart mode is a firmware toggle; only press when it needs to flip.
        if self.smart_mode != enabled:
            await self._send_key(KEY_SMART_MODE)
        self.smart_mode = enabled
        self.push_update()

    async def set_pure_voice(self, enabled: bool) -> None:
        if self._client is None:
            self._client = JBLClient(self._device_config.host)
            await self._client.connect()
        await self._client.set_pure_voice(enabled)
        self.pure_voice = enabled
        self.push_update()

    async def set_eq_preset(self, name: str) -> bool:
        for eq_id, eq_name in self.eq_preset_map.items():
            if eq_name == name:
                preset = self.eq_preset_data.get(eq_id, {})
                if self._client is None:
                    self._client = JBLClient(self._device_config.host)
                    await self._client.connect()
                ok = await self._client.set_active_eq_preset(eq_id, preset)
                if ok:
                    self.eq_active_name = name
                    self.push_update()
                return ok
        _LOG.warning("[%s] EQ preset not found: %s", self.log_id, name)
        return False
