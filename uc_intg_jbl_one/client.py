"""Async client for JBL One (LinkPlay / Harman) soundbars.

Two protocols are used:

* **httpapi.asp** over HTTPS (mutual TLS, self-signed server cert) - key presses
  (``sendAppController``) and all ``get*/set*`` config commands (EQ, night mode,
  pure voice, smart mode, rear speakers).
* **UPnP SOAP** over plain HTTP on port 59152 - playback state (``GetInfoEx``),
  volume (``SetVolume``) and the product/model info (``GetControlDeviceInfo``).

The SSL context (with the embedded client identity) is built once at import so
it never blocks the event loop on a request (upstream HA issue #33). A single
aiohttp session is reused for the client's whole lifetime.
"""

import asyncio
import json
import logging
import os
import ssl
import tempfile
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp

from uc_intg_jbl_one.certs import CLIENT_CERT_PEM, CLIENT_KEY_PEM
from uc_intg_jbl_one.const import UPNP_PORT

_LOG = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=10)


def _create_ssl_context() -> ssl.SSLContext:
    """Build the mTLS client context with the embedded LinkPlay identity."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cert_file = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False, encoding="utf-8")
    key_file = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False, encoding="utf-8")
    try:
        cert_file.write(CLIENT_CERT_PEM)
        cert_file.close()
        key_file.write(CLIENT_KEY_PEM)
        key_file.close()
        ctx.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
    finally:
        for path in (cert_file.name, key_file.name):
            try:
                os.unlink(path)
            except OSError:
                pass
    return ctx


# Built once - the embedded identity never changes.
_SSL_CONTEXT = _create_ssl_context()


class JBLClient:
    """Async client for one JBL soundbar (single session per lifetime)."""

    def __init__(self, host: str) -> None:
        self.host = host
        self._session: aiohttp.ClientSession | None = None
        self.firmware: str = ""
        self.new_firmware: bool = False

    @property
    def is_connected(self) -> bool:
        return self._session is not None and not self._session.closed

    async def connect(self) -> bool:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_TIMEOUT)
        return True

    async def close(self) -> None:
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            self._session = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_TIMEOUT)
        return self._session

    # -- httpapi.asp (HTTPS, client cert) ------------------------------
    async def _api_get(self, command: str) -> dict[str, Any]:
        session = await self._ensure_session()
        url = f"https://{self.host}/httpapi.asp?command={command}"
        headers = {"Accept-Encoding": "gzip"}
        async with session.get(url, headers=headers, ssl=_SSL_CONTEXT) as response:
            if response.status != 200:
                _LOG.debug("GET %s -> HTTP %s", command, response.status)
                return {}
            text = await response.text()
            try:
                return json.loads(text)
            except (ValueError, json.JSONDecodeError):
                _LOG.debug("GET %s returned non-JSON: %s", command, text[:120])
                return {}

    async def _api_post(self, payload: str) -> bool:
        session = await self._ensure_session()
        url = f"https://{self.host}/httpapi.asp"
        headers = {"Accept-Encoding": "gzip"}
        async with session.post(url, data=payload, headers=headers, ssl=_SSL_CONTEXT) as response:
            if response.status != 200:
                _LOG.warning("POST failed (HTTP %s): %s", response.status, payload[:80])
                return False
            return True

    async def send_key(self, key: str) -> bool:
        """Send a sendAppController key press."""
        payload = f'command=sendAppController&payload={{"key_pressed": "{key}"}}'
        return await self._api_post(payload)

    # -- UPnP SOAP (HTTP :59152) ---------------------------------------
    async def _soap(self, control: str, action: str, body: str) -> str | None:
        session = await self._ensure_session()
        url = f"http://{self.host}:{UPNP_PORT}/upnp/control/{control}"
        headers = {
            "Content-type": 'text/xml;charset="utf-8"',
            "Soapaction": f'"urn:schemas-upnp-org:service:{action}"',
        }
        async with session.post(url, data=body, headers=headers) as response:
            if response.status != 200:
                _LOG.debug("SOAP %s -> HTTP %s", action, response.status)
                return None
            return await response.text()

    async def get_device_type(self) -> dict[str, Any]:
        """Return {hm_product_name, hardware, ...}. Doubles as reachability probe."""
        body = (
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
            '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"'
            ' xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
            '<u:GetControlDeviceInfo xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">'
            "<InstanceID>0</InstanceID></u:GetControlDeviceInfo></s:Body></s:Envelope>"
        )
        text = await self._soap(
            "rendercontrol1", "RenderingControl:1#GetControlDeviceInfo", body
        )
        if not text:
            return {}
        try:
            root = ET.fromstring(text)
            ns = {
                "s": "http://schemas.xmlsoap.org/soap/envelope/",
                "u": "urn:schemas-upnp-org:service:RenderingControl:1",
            }
            status = root.find(".//u:GetControlDeviceInfoResponse/Status", ns)
            if status is not None and status.text:
                return json.loads(status.text)
        except (ET.ParseError, ValueError, json.JSONDecodeError) as err:
            _LOG.debug("Parsing device type failed: %s", err)
        return {}

    async def get_device_info(self) -> dict[str, Any]:
        """Return the device_info block (mac, uuid, name, serial, firmware)."""
        data = await self._api_get("getDeviceInfo")
        info = data.get("device_info", {}) if isinstance(data, dict) else {}
        firmware = info.get("firmware", "")
        self.firmware = firmware
        self.new_firmware = _is_new_firmware(firmware)
        return info

    async def get_playback_info(self) -> dict[str, Any]:
        """Return parsed GetInfoEx playback fields (best-effort)."""
        body = (
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
            '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"'
            ' xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
            '<u:GetInfoEx xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">'
            "<InstanceID>0</InstanceID></u:GetInfoEx></s:Body></s:Envelope>"
        )
        text = await self._soap("rendertransport1", "AVTransport:1#GetInfoEx", body)
        if not text:
            return {}
        try:
            root = ET.fromstring(text)
        except ET.ParseError as err:
            _LOG.debug("Parsing playback info failed: %s", err)
            return {}
        ns = {
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
            "u": "urn:schemas-upnp-org:service:AVTransport:1",
        }

        def _field(tag: str) -> str:
            node = root.find(f".//u:GetInfoExResponse/{tag}", ns)
            return node.text if node is not None and node.text is not None else ""

        return {
            "play_medium": _field("PlayMedium"),
            "volume_level": _field("CurrentVolume"),
            "track": _field("TrackURI"),
            "transport_state": _field("CurrentTransportState"),
            "transport_status": _field("CurrentTransportStatus"),
            "track_duration": _field("TrackDuration"),
            "mute": _field("CurrentMute"),
            "channel": _field("CurrentChannel"),
        }

    async def set_volume(self, value: int) -> bool:
        body = (
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
            '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"'
            ' xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
            '<u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">'
            "<InstanceID>0</InstanceID><Channel>Single</Channel>"
            f"<DesiredVolume>{int(round(value))}</DesiredVolume>"
            "</u:SetVolume></s:Body></s:Envelope>"
        )
        text = await self._soap("rendercontrol1", "RenderingControl:1#SetVolume", body)
        return text is not None

    # -- config get/set (httpapi) --------------------------------------
    async def get_night_mode(self) -> str | None:
        data = await self._api_get("getPersonalListeningMode")
        return data.get("status") if isinstance(data, dict) and "status" in data else None

    async def set_night_mode(self, enabled: bool) -> bool:
        value = "on" if enabled else "off"
        return await self._api_post(
            f'command=setPersonalListeningMode&payload={{"status":"{value}"}}'
        )

    async def get_smart_mode(self) -> str | None:
        data = await self._api_get("getSmartMode")
        return data.get("status") if isinstance(data, dict) and "status" in data else None

    async def get_pure_voice(self) -> str | None:
        data = await self._api_get("getPureVoiceState")
        if isinstance(data, dict) and "purevoice_state" in data:
            return "on" if data["purevoice_state"] == "1" else "off"
        return None

    async def set_pure_voice(self, enabled: bool) -> bool:
        value = "1" if enabled else "0"
        return await self._api_post(
            f'command=setPureVoiceState&payload={{"purevoice_state":"{value}"}}'
        )

    async def get_rear_speakers(self) -> list[dict[str, Any]]:
        data = await self._api_get("getRearSpeakerStatus")
        rears = data.get("rears") if isinstance(data, dict) else None
        return rears if isinstance(rears, list) else []

    async def get_eq_presets(self) -> dict[str, Any]:
        """Return {preset_map, preset_data, active_id, active_name} (new firmware)."""
        if not self.new_firmware:
            return {}
        data = await self._api_get("getEQList")
        if not isinstance(data, dict):
            return {}
        eq_list = data.get("eq_list", []) or []
        active_id = str(data.get("active_eq_id", "0"))
        preset_map: dict[str, str] = {}
        preset_data: dict[str, dict[str, Any]] = {}
        active_name: str | None = None
        for item in eq_list:
            eq_id = str(item.get("eq_id", ""))
            eq_name = item.get("eq_name", f"Preset {eq_id}")
            preset_map[eq_id] = eq_name
            preset_data[eq_id] = item
            if eq_id == active_id:
                active_name = eq_name
        if not active_name and preset_map:
            active_name = next(iter(preset_map.values()))
        if not preset_map:
            return {}
        return {
            "preset_map": preset_map,
            "preset_data": preset_data,
            "active_id": active_id,
            "active_name": active_name,
        }

    async def set_active_eq_preset(self, eq_id: str, preset: dict[str, Any]) -> bool:
        send_payload = json.dumps(
            {
                "active_eq_id": eq_id,
                "band": preset.get("band", 7),
                "eq_payload": preset.get("eq_payload", {}),
            }
        )
        return await self._api_post(f"command=setActiveEQ&payload={send_payload}")


def _is_new_firmware(firmware: str) -> bool:
    """Detect JBL One 3.0+ (7-band EQ + presets). Guarded against odd strings."""
    try:
        parts = firmware.split(".")
        return int(parts[0]) > 24 or int(parts[2]) > 31
    except (ValueError, IndexError):
        return False


async def is_reachable(host: str, timeout: float = 3.0) -> bool:
    """Quick reachability probe using the UPnP device-info endpoint."""
    client = JBLClient(host)
    try:
        await client.connect()
        info = await asyncio.wait_for(client.get_device_type(), timeout=timeout)
        return bool(info.get("hm_product_name", "unknown_product") != "unknown_product")
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
        return False
    finally:
        await client.close()
