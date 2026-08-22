"""JBL soundbar sensor entities (model, firmware, rear-speaker battery)."""

import logging

from ucapi import sensor
from ucapi_framework import SensorEntity

from uc_intg_jbl_one.config import JBLConfig
from uc_intg_jbl_one.const import STATE_ON, STATE_STANDBY
from uc_intg_jbl_one.device import JBLDevice

_LOG = logging.getLogger(__name__)


class ModelSensor(SensorEntity):
    """Reports the soundbar model."""

    def __init__(self, device_config: JBLConfig, device: JBLDevice) -> None:
        self._device = device
        super().__init__(
            f"sensor.{device_config.identifier}.model",
            f"{device_config.name} Model",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        self.update(
            {sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: self._device.model or "Unknown"}
        )


class FirmwareSensor(SensorEntity):
    """Reports the soundbar firmware version."""

    def __init__(self, device_config: JBLConfig, device: JBLDevice) -> None:
        self._device = device
        super().__init__(
            f"sensor.{device_config.identifier}.firmware",
            f"{device_config.name} Firmware",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
            options={sensor.Options.CUSTOM_UNIT: ""},
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        self.update(
            {sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: self._device.firmware or "Unknown"}
        )


class RearBatterySensor(SensorEntity):
    """Battery level of a detachable rear speaker."""

    def __init__(self, device_config: JBLConfig, device: JBLDevice, index: int, channel: str) -> None:
        self._device = device
        self._index = index
        label = f"Rear {channel.title()} Battery" if channel else f"Rear {index + 1} Battery"
        super().__init__(
            f"sensor.{device_config.identifier}.rear_battery_{index}",
            f"{device_config.name} {label}",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: 0},
            device_class=sensor.DeviceClasses.BATTERY,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        rears = self._device.rears
        if self._device.state not in (STATE_ON, STATE_STANDBY) or self._index >= len(rears):
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        capacity = rears[self._index].get("capicity", 0)
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: capacity})


def create_sensors(device_config: JBLConfig, device: JBLDevice) -> list[SensorEntity]:
    entities: list[SensorEntity] = [
        ModelSensor(device_config, device),
        FirmwareSensor(device_config, device),
    ]
    for index, rear in enumerate(device.rears):
        channel = str(rear.get("channel", "")) if isinstance(rear, dict) else ""
        entities.append(RearBatterySensor(device_config, device, index, channel))
    return entities
