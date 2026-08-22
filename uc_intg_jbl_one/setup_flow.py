"""Setup flow: discover JBL soundbars via mDNS, or enter an IP manually."""

import logging
import re
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_jbl_one import discovery
from uc_intg_jbl_one.client import JBLClient
from uc_intg_jbl_one.config import JBLConfig

_LOG = logging.getLogger(__name__)


class JBLSetupFlow(BaseSetupFlow[JBLConfig]):
    """Discover JBL soundbars and add the chosen one."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._devices: list[dict[str, str]] = []

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "JBL Soundbar Setup"},
            [
                {
                    "id": "info",
                    "label": {"en": "JBL One Soundbar"},
                    "field": {"label": {"value": {"en": (
                        "Your JBL soundbars are discovered automatically on the network. "
                        "Leave the IP address blank to auto-discover, or enter it manually "
                        "if discovery does not find your soundbar. The soundbar must be "
                        "powered on and connected to your network."
                    )}}},
                },
                {
                    "id": "host",
                    "label": {"en": "IP Address (optional)"},
                    "field": {"text": {"value": ""}},
                },
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> JBLConfig | RequestUserInput:
        host = input_values.get("host", "").strip()

        if host:
            return await self._build_from_host(host, "")

        _LOG.info("Discovering JBL soundbars on the network...")
        self._devices = await discovery.discover(timeout=6.0)
        _LOG.info("Discovered %d JBL soundbar(s)", len(self._devices))

        if not self._devices:
            raise ValueError(
                "No JBL soundbars were found on the network. Make sure the soundbar is "
                "powered on and on the same network as the Remote, then try again and "
                "enter the IP address manually."
            )

        if len(self._devices) == 1:
            dev = self._devices[0]
            return await self._build_from_host(dev["host"], dev.get("uuid", ""))

        items = [{"id": d["host"], "label": {"en": f"{d['name']} ({d['host']})"}} for d in self._devices]
        return RequestUserInput(
            {"en": "Select JBL Soundbar"},
            [{
                "id": "device",
                "label": {"en": "Device"},
                "field": {"dropdown": {"value": items[0]["id"], "items": items}},
            }],
        )

    async def handle_additional_configuration_response(self, msg: Any) -> JBLConfig | None:
        host = msg.input_values.get("device", "")
        dev = next((d for d in self._devices if d["host"] == host), None)
        if not dev:
            raise ValueError("Selected device not found")
        self._pending_device_config = await self._build_from_host(dev["host"], dev.get("uuid", ""))
        return None

    async def _build_from_host(self, host: str, uuid: str) -> JBLConfig:
        client = JBLClient(host)
        try:
            await client.connect()
            device_type = await client.get_device_type()
            model = device_type.get("hm_product_name", "") if device_type else ""
            if not model or model == "unknown_product":
                raise ValueError(
                    f"Could not reach a JBL soundbar at {host}. Check the IP address and "
                    "make sure the soundbar is powered on and on the same network."
                )
            info = await client.get_device_info()
        finally:
            await client.close()

        uuid = uuid or (info.get("uuid", "") if info else "")
        mac = info.get("wlan0_mac", "") if info else ""
        name = model or (info.get("name", "") if info else "") or "JBL Soundbar"

        base = uuid or host
        identifier = f"jbl_{re.sub(r'[^A-Za-z0-9]', '_', base)}"
        return JBLConfig(identifier=identifier, name=name, host=host, uuid=uuid, mac=mac, model=model)
